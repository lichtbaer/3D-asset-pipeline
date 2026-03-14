import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSubagentTasks, integrateTask, type SubagentTask } from "../../api/aria.js";
import { useI18n } from "../../hooks/useI18n.js";
import "./SubagentTaskPanel.css";

function formatAge(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h`;
  return `${Math.floor(secs / 86400)}d`;
}

function TaskRow({
  task,
  onIntegrate,
  t,
}: {
  task: SubagentTask;
  onIntegrate: (id: string) => void;
  t: (k: string) => string;
}) {
  const typeLabel = t(`tasks.type.${task.type}`) || task.type;
  const statusLabel = t(`tasks.status.${task.status}`) || task.status;
  const canIntegrate =
    task.status === "completed" && !task.integrated_at;

  return (
    <div className="subagent-task-row" data-status={task.status}>
      <span className="subagent-task-type">{typeLabel}</span>
      <span className={`subagent-task-badge subagent-task-badge--${task.status}`}>
        {statusLabel}
      </span>
      <span className="subagent-task-subproject">{task.subproject_id}</span>
      <span className="subagent-task-age">{formatAge(task.created_at)}</span>
      {task.last_heartbeat_at && (
        <span className="subagent-task-heartbeat">
          ♥ {formatAge(task.last_heartbeat_at)}
        </span>
      )}
      {canIntegrate && (
        <button
          type="button"
          className="subagent-task-integrate"
          onClick={() => onIntegrate(task.id)}
        >
          {t("tasks.panel.integrate")}
        </button>
      )}
    </div>
  );
}

export function SubagentTaskPanel() {
  const { t } = useI18n("de");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["subagent-tasks"],
    queryFn: getSubagentTasks,
    refetchInterval: 10_000,
  });

  const integrateMutation = useMutation({
    mutationFn: integrateTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subagent-tasks"] });
    },
  });

  const handleIntegrate = (taskId: string) => {
    integrateMutation.mutate(taskId);
  };

  const active = data?.active ?? [];
  const recent = data?.recent ?? [];
  const hasAny = active.length > 0 || recent.length > 0;

  return (
    <aside className="subagent-task-panel">
      <h3 className="subagent-task-panel__title">{t("tasks.panel.title")}</h3>
      {isLoading && <p className="subagent-task-panel__loading">Laden…</p>}
      {!isLoading && !hasAny && (
        <p className="subagent-task-panel__empty">{t("tasks.panel.empty")}</p>
      )}
      {!isLoading && hasAny && (
        <>
          {active.length > 0 && (
            <section>
              <h4 className="subagent-task-panel__section">
                {t("tasks.panel.active")}
              </h4>
              {active.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  onIntegrate={handleIntegrate}
                  t={t}
                />
              ))}
            </section>
          )}
          {recent.length > 0 && (
            <section>
              <h4 className="subagent-task-panel__section">
                {t("tasks.panel.recent")}
              </h4>
              {recent.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  onIntegrate={handleIntegrate}
                  t={t}
                />
              ))}
            </section>
          )}
        </>
      )}
      {integrateMutation.isError && (
        <p className="subagent-task-panel__error">
          Fehler beim Integrieren
        </p>
      )}
    </aside>
  );
}

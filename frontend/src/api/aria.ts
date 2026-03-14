import { apiClient } from "./client.js";

const COMPANY_ID = "default";

export interface SubagentTask {
  id: string;
  type: string;
  status: string;
  subproject_id: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  created_at: string | null;
  last_heartbeat_at: string | null;
  integrated_at: string | null;
}

export interface TasksResponse {
  active: SubagentTask[];
  recent: SubagentTask[];
}

export async function getSubagentTasks(): Promise<TasksResponse> {
  const { data } = await apiClient.get<TasksResponse>(
    `/api/v1/companies/${COMPANY_ID}/aria/tasks`
  );
  return data;
}

export async function integrateTask(taskId: string): Promise<{
  summary: string;
  integrated: boolean;
}> {
  const { data } = await apiClient.post<{ summary: string; integrated: boolean }>(
    `/api/v1/companies/${COMPANY_ID}/aria/integrate-task`,
    { task_id: taskId }
  );
  return data;
}

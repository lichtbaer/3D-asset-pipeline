import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPromptHistory } from "../api/prompts.js";

const FAVORITES_KEY = "promptFavorites";

function loadFavorites(): Set<string> {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (raw) {
      const arr = JSON.parse(raw) as unknown;
      if (Array.isArray(arr)) return new Set(arr as string[]);
    }
  } catch {
    // ignore parse errors
  }
  return new Set();
}

function saveFavorites(favorites: Set<string>): void {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
  } catch {
    // ignore storage errors
  }
}

export function usePromptHistory() {
  const [favorites, setFavoritesState] = useState<Set<string>>(loadFavorites);

  const { data: historyItems = [] } = useQuery({
    queryKey: ["promptHistory"],
    queryFn: () => getPromptHistory(30),
    staleTime: 30_000,
  });

  const toggleFavorite = useCallback((prompt: string) => {
    setFavoritesState((prev) => {
      const next = new Set(prev);
      if (next.has(prompt)) {
        next.delete(prompt);
      } else {
        next.add(prompt);
      }
      saveFavorites(next);
      return next;
    });
  }, []);

  const isFavorite = useCallback(
    (prompt: string) => favorites.has(prompt),
    [favorites]
  );

  return { historyItems, favorites, toggleFavorite, isFavorite };
}

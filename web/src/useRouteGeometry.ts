import { useEffect, useState } from "react";
import { api } from "./api";
import { useAuth } from "./auth";

export type LatLon = [number, number];

export function useRouteGeometry(routeId: number | null | undefined) {
  const { token } = useAuth();
  const [geometry, setGeometry] = useState<LatLon[] | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token || !routeId) {
      setGeometry(null);
      setSource(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setGeometry(null);
    setSource(null);
    api
      .routeGeometry(token, routeId)
      .then((result) => {
        if (!cancelled) {
          setGeometry(result.coordinates);
          setSource(result.source);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGeometry(null);
          setSource(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, routeId]);

  return { geometry, source, loading };
}

import { useEffect, useState } from "react";
import axios from "axios";
import { API_URL } from "../config";
import { useAuth } from "../auth/AuthContext";
import { isOwnerEmail, readOwnerCache, writeOwnerCache } from "../lib/owner";

const inflight = new Map<string, Promise<boolean>>();

const readUserId = (): string | null => {
  try {
    return localStorage.getItem("userId");
  } catch {
    return null;
  }
};

const lookupOwner = (userId: string): Promise<boolean> => {
  const cached = readOwnerCache(userId);
  if (cached !== null) return Promise.resolve(cached);
  const pending = inflight.get(userId);
  if (pending) return pending;
  const p = axios
    .get(`${API_URL}/users/${userId}/profile`)
    .then((res) => {
      const owner = isOwnerEmail(res.data?.user?.email);
      writeOwnerCache(userId, owner);
      return owner;
    })
    .catch(() => false)
    .finally(() => inflight.delete(userId));
  inflight.set(userId, p);
  return p;
};

/**
 * True only for the app owner's account. Unknown reads as false, so bowling
 * and golf surfaces stay hidden until the profile email is known.
 */
export const useIsOwner = (): boolean => {
  const { user } = useAuth();
  const authOwner = isOwnerEmail(user?.email);
  const userId = readUserId();
  const [owner, setOwner] = useState<boolean>(() => (userId ? readOwnerCache(userId) === true : false));

  useEffect(() => {
    if (authOwner || !userId) return;
    let cancelled = false;
    lookupOwner(userId).then((v) => {
      if (!cancelled) setOwner(v);
    });
    return () => {
      cancelled = true;
    };
  }, [authOwner, userId]);

  return authOwner || owner;
};

export default useIsOwner;

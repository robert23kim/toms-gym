import React, { useEffect, useState } from "react";
import {
  fetchAchievements,
  setAvatar,
  AchievementsResponse,
} from "../../lib/api";

interface AvatarPickerProps {
  userId: string;
  /** Called with the new avatar URL once the server accepts the pick. */
  onSelected: (avatarUrl: string) => void;
}

/**
 * Owner-only avatar chooser: unlocked packs are selectable, locked ones show
 * the milestone that opens them (👑 Champion unlocks by winning a challenge).
 */
const AvatarPicker: React.FC<AvatarPickerProps> = ({ userId, onSelected }) => {
  const [data, setData] = useState<AchievementsResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchAchievements(userId)
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setSelected(res.avatar);
      })
      .catch(() => {}); // non-fatal: picker simply stays hidden
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!data) return null;

  const pick = async (key: string, url: string) => {
    const previous = selected;
    setSelected(key);
    setError(false);
    try {
      await setAvatar(userId, key);
      onSelected(url);
    } catch {
      setSelected(previous);
      setError(true);
    }
  };

  return (
    <div className="bg-card rounded-xl p-6 mb-6 shadow-sm">
      <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-4">
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
        Your avatar
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
      </div>

      <div className="flex flex-wrap gap-3">
        {data.avatars.map((a) => (
          <button
            key={a.key}
            type="button"
            aria-label={`Choose avatar ${a.key}`}
            onClick={() => pick(a.key, a.url)}
            className={`h-14 w-14 rounded-full overflow-hidden border-2 transition-colors ${
              selected === a.key
                ? "border-accent"
                : "border-transparent hover:border-border"
            }`}
          >
            <img src={a.url} alt="" className="h-full w-full object-cover" />
          </button>
        ))}
      </div>

      {error && (
        <p className="mt-3 text-sm text-destructive">
          Could not save that avatar. Please try again.
        </p>
      )}

      {data.locked_packs.length > 0 && (
        <div className="mt-5 flex flex-col gap-2">
          {data.locked_packs.map((p) => (
            <div
              key={p.key}
              data-testid={`locked-pack-${p.key}`}
              className="flex items-center gap-2 text-sm text-muted-foreground opacity-70"
            >
              <span aria-hidden="true">{p.emoji}</span>
              <span className="font-medium">{p.title}</span>
              <span>— {p.hint}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AvatarPicker;

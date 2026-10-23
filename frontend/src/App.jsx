import { useEffect, useState } from 'react';

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api')
  .replace(/\/$/, '');

const roleColors = {
  Initiator: '#7c3aed',
  Admin: '#2563eb',
  Debater: '#0f766e',
  Viewer: '#64748b',
};

const makeProfile = () => {
  const raw =
    globalThis.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  const id = `DBT-${raw.replace(/-/g, '').slice(0, 8).toUpperCase()}`;

  return {
    id,
    name: `Debater-${id.slice(-4)}`,
    role: 'Viewer',
    color: roleColors.Viewer,
  };
};

const readProfile = () => {
  try {
    const saved = JSON.parse(
      localStorage.getItem('debatence-profile') || 'null'
    );

    return saved?.id ? saved : makeProfile();
  } catch {
    return makeProfile();
  }
};

const label = {
  needs_review: 'Needs evidence',
  valid: 'Supported',
  invalid: 'Contradicted',
  unverified: 'Unclear',
  correct: 'Supported',
  incorrect: 'Contradicted',
};

export default function App() {
  const [debates, setDebates] = useState([]);
  const [active, setActive] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [search, setSearch] = useState('');
  const [debateStats, setDebateStats] = useState(null);

  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState('');
  const [commentSort, setCommentSort] = useState('newest');
  const [commentsOpen, setCommentsOpen] = useState(false);

  const [profile, setProfile] = useState(readProfile);

  const [ownedDebates, setOwnedDebates] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem('debatence-owned-debates') || '[]'
      );
    } catch {
      return [];
    }
  });

  const [debateRole, setDebateRole] = useState('Viewer');
  const [serverRoleRequests, setServerRoleRequests] = useState([]);
  const [requestPending, setRequestPending] = useState(false);

  const {
    id: userId,
    name: author,
    role: profileRole,
    color: profileColor,
  } = profile;

  const isActiveCreator =
    !!active && ownedDebates.includes(active.id);

  const role = isActiveCreator ? 'Initiator' : debateRole;

  const updateProfile = (patch) =>
    setProfile((current) => {
      const next = { ...current, ...patch };

      localStorage.setItem('debatence-profile', JSON.stringify(next));

      return next;
    });

  // Continue with the remaining App.jsx code here.
}

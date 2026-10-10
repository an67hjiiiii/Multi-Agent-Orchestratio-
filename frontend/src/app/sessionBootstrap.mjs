export async function bootstrapWorkspace(api) {
  let session;
  try {
    session = await api.currentSession();
  } catch (error) {
    if (error?.status !== 401) throw error;
    const [health] = await Promise.allSettled([api.health()]);
    return {
      authenticated: false,
      user: null,
      health,
      sources: null,
      history: null,
    };
  }

  if (!session?.authenticated) {
    const [health] = await Promise.allSettled([api.health()]);
    return {
      authenticated: false,
      user: null,
      health,
      sources: null,
      history: null,
    };
  }

  const [health, sources, history] = await Promise.allSettled([
    api.health(),
    api.listSources(),
    api.listRuns(),
  ]);
  return {
    authenticated: true,
    user: session.user,
    health,
    sources,
    history,
  };
}

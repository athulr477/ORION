import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchWorkspaces, setWorkspaceId } from '../api/client';

const WorkspaceContext = createContext();

export function useWorkspace() {
  return useContext(WorkspaceContext);
}

export function WorkspaceProvider({ children, currentUser }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentUser) {
      setWorkspaces([]);
      setCurrentWorkspace(null);
      setWorkspaceId(null);
      setLoading(false);
      return;
    }

    let isMounted = true;
    setLoading(true);

    fetchWorkspaces()
      .then((data) => {
        if (!isMounted) return;
        setWorkspaces(data);

        // Check if there's a saved workspace in localStorage
        const savedWorkspaceId = localStorage.getItem('orion_workspace_id');
        let selected = null;

        if (savedWorkspaceId) {
          selected = data.find((ws) => ws.id === savedWorkspaceId);
        }

        // If no saved workspace or invalid, pick the first one
        if (!selected && data.length > 0) {
          selected = data[0];
        }

        if (selected) {
          setCurrentWorkspace(selected);
          setWorkspaceId(selected.id);
          localStorage.setItem('orion_workspace_id', selected.id);
        }
      })
      .catch((err) => {
        console.error("Failed to load workspaces:", err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [currentUser]);

  const switchWorkspace = (workspaceId) => {
    const selected = workspaces.find((ws) => ws.id === workspaceId);
    if (selected) {
      setCurrentWorkspace(selected);
      setWorkspaceId(selected.id);
      localStorage.setItem('orion_workspace_id', selected.id);
      // Optional: Refresh the page or trigger a re-fetch of matrix data
      window.dispatchEvent(new Event('workspaceChange'));
    }
  };

  const value = {
    workspaces,
    currentWorkspace,
    switchWorkspace,
    loading,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

/**
 * NotificationBell — PRD Module 1 (Phase 14).
 *
 * Interactive notification bell with unread badge counter and dropdown tray
 * for real-time build, test-run, defence, and safety alerts.
 */

import { useState, useRef, useEffect } from 'react';
import {
  Bell,
  CheckCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  XCircle,
  ExternalLink,
  Shield,
  Box,
  Play,
  Users,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import './NotificationBell.css';

export interface NotificationItem {
  id: string;
  org_id: string;
  user_id?: string | null;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  category: 'build' | 'test_run' | 'invitation' | 'defence' | 'safety' | 'general';
  read: boolean;
  link?: string | null;
  created_at: string;
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch unread count
  const { data: countData } = useQuery<{ unread_count: number }>({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => {
      const res = await fetch('/api/notifications/unread-count', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!res.ok) return { unread_count: 0 };
      return res.json();
    },
    refetchInterval: 15000,
  });

  // Fetch recent notifications when dropdown is opened
  const { data: notifications = [], refetch } = useQuery<NotificationItem[]>({
    queryKey: ['notifications', 'list'],
    queryFn: async () => {
      const res = await fetch('/api/notifications?limit=25', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!res.ok) return [];
      return res.json();
    },
    enabled: isOpen,
  });

  // Mark all as read mutation
  const markAllReadMutation = useMutation({
    mutationFn: async () => {
      await fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Mark single as read mutation
  const markSingleReadMutation = useMutation({
    mutationFn: async (id: string) => {
      await fetch(`/api/notifications/${id}/read`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const unreadCount = countData?.unread_count || 0;

  const handleItemClick = (item: NotificationItem) => {
    if (!item.read) {
      markSingleReadMutation.mutate(item.id);
    }
    if (item.link) {
      setIsOpen(false);
      navigate(item.link);
    }
  };

  const getCategoryIcon = (category: string, type: string) => {
    switch (category) {
      case 'build':
        return <Box size={14} className="notif-cat-icon text-info" />;
      case 'test_run':
        return <Play size={14} className="notif-cat-icon text-accent" />;
      case 'defence':
        return <Shield size={14} className="notif-cat-icon text-primary" />;
      case 'invitation':
        return <Users size={14} className="notif-cat-icon text-warning" />;
      default:
        if (type === 'error') return <XCircle size={14} className="notif-cat-icon text-danger" />;
        if (type === 'warning') return <AlertTriangle size={14} className="notif-cat-icon text-warning" />;
        if (type === 'success') return <CheckCircle2 size={14} className="notif-cat-icon text-success" />;
        return <Info size={14} className="notif-cat-icon text-info" />;
    }
  };

  return (
    <div className="notification-bell-container" ref={containerRef}>
      <button
        type="button"
        className={`notification-bell-btn ${unreadCount > 0 ? 'has-unread' : ''}`}
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) refetch();
        }}
        aria-label="Platform Notifications"
        title="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="notification-badge font-mono">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-dropdown-header">
            <div className="notif-title-group">
              <span className="notif-header-title font-display">Notifications</span>
              {unreadCount > 0 && (
                <span className="notif-header-count badge badge-primary font-mono">
                  {unreadCount} unread
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                className="notif-mark-all-btn font-mono"
                onClick={() => markAllReadMutation.mutate()}
                disabled={markAllReadMutation.isPending}
              >
                <CheckCheck size={13} />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty">
                <Bell size={28} className="text-muted" />
                <p className="notif-empty-text">No notifications yet</p>
                <span className="notif-empty-sub font-mono">
                  Platform alerts and test completion notices will appear here.
                </span>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`notification-item ${!item.read ? 'unread' : 'read'}`}
                  onClick={() => handleItemClick(item)}
                >
                  <div className="notif-icon-col">
                    {getCategoryIcon(item.category, item.type)}
                  </div>
                  <div className="notif-content-col">
                    <div className="notif-item-header">
                      <span className="notif-item-title font-display">{item.title}</span>
                      <span className="notif-item-time font-mono">
                        {new Date(item.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="notif-item-message">{item.message}</p>
                    {item.link && (
                      <span className="notif-item-link font-mono">
                        <span>View details</span>
                        <ExternalLink size={10} />
                      </span>
                    )}
                  </div>
                  {!item.read && <div className="notif-unread-dot" />}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

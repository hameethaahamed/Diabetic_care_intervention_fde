INSERT INTO intervention_statuses (status, sort_order) VALUES
    ('PENDING_REVIEW', 1),
    ('ASSIGNED', 2),
    ('CONTACTED', 3),
    ('FOLLOW_UP_SCHEDULED', 4),
    ('CLOSED', 5)
ON CONFLICT (status) DO NOTHING;

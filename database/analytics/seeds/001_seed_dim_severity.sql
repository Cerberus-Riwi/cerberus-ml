INSERT INTO analytics.dim_severity (
    severity_name,
    priority,
    color,
    sla_days
)
VALUES
    ('critical', 1, '#DC2626', 1),
    ('high',     2, '#EA580C', 7),
    ('medium',   3, '#D97706', 30),
    ('low',      4, '#2563EB', 90),
    ('info',     5, '#6B7280', NULL)
ON CONFLICT (severity_name)
DO NOTHING;
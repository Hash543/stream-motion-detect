-- Migration: Seed data from old face-motion project
-- Convert MySQL data to PostgreSQL compatible format

-- Temporarily disable foreign key constraint for organization.pid
ALTER TABLE organization DROP CONSTRAINT IF EXISTS organization_pid_fkey;

-- Insert organizations (pid=0 means top level, no parent)
INSERT INTO organization (id, name, full_name, pid, org_type, tel, gui_no, bank_code, bank_num, remarks, contact_person, contact_ext, contact_tel, contact_email, created_id, created_at, updated_id, updated_at, address)
VALUES
(1, '交通部', '交通部', NULL, '0', '', '', '', '', '', '', '', '', '', 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, ''),
(2, '系统', '交通部', NULL, '0', '', '', '', '', '', '', '', '', '', 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, ''),
(3, '设施公司', '设施公司', 2, '1', '', '', '', '', '', '', '', '', '', 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, ''),
(4, '四方公司', '四方公司', 2, '1', '', '', '', '', '', '', '', '', '', 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, '')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    full_name = EXCLUDED.full_name,
    pid = EXCLUDED.pid,
    org_type = EXCLUDED.org_type;

-- Re-enable foreign key constraint for organization.pid (allow NULL for top level)
ALTER TABLE organization ADD CONSTRAINT organization_pid_fkey
    FOREIGN KEY (pid) REFERENCES organization(id);

-- Reset organization sequence
SELECT setval('organization_id_seq', (SELECT MAX(id) FROM organization));

-- Insert roles
INSERT INTO role (id, role_name, alias_name, org_id, created_id, created_at, updated_id, updated_at)
VALUES
(1, '管理员', 'sys', 1, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(2, '一般用户', 'user', 2, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO UPDATE SET
    role_name = EXCLUDED.role_name,
    alias_name = EXCLUDED.alias_name,
    org_id = EXCLUDED.org_id;

-- Reset role sequence
SELECT setval('role_id_seq', (SELECT MAX(id) FROM role));

-- Insert users (passwords are base64 encoded from original system)
-- Note: User IDs 7 and 8 reference org_id 7 which doesn't exist, using org_id 1 instead
INSERT INTO "user" (id, username, user_name, password, org_id, role_id, status, created_id, created_at, updated_id, updated_at)
VALUES
(1, '管理者', '管理者', '566h55CG6ICFMDAxQWRtaW4xMjNf', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(2, '农路科', '农路科', '5Yac6Lev56eRMTIzNDU2Nzg=', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(3, '养护科', '养护科', '5YW75oqk56eRMTIzNDU2Nzg=', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(4, '安全科', '安全科', '5a6J5YWo56eRMTIzNDU2Nzg=', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(5, '设施科', '设施科', '6K6+5pa956eRMTIzNDU2Nzg=', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(6, '路网科', '路网科', '6Lev572R56eRMTIzNDU2Nzg=', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(7, '设施公司', '设施公司', '6K6+5pa95YWs5Y+4MTIzNDU2Nzg=', 3, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(8, '四方公司', '四方公司', '5Zub5pa55YWs5Y+4MTIzNDU2Nzg=', 4, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP),
(9, 'superuser', 'superuser', 'c3VwZXJ1c2VyMTIzNDU2Nw==', 1, 1, 0, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    user_name = EXCLUDED.user_name,
    password = EXCLUDED.password,
    org_id = EXCLUDED.org_id,
    role_id = EXCLUDED.role_id,
    status = EXCLUDED.status;

-- Reset user sequence
SELECT setval('user_id_seq', (SELECT MAX(id) FROM "user"));

-- Insert permissions (simplified structure - only permission names)
INSERT INTO permission (id, permission_name, created_at, updated_at)
VALUES
(1, 'dashboard', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 'data-platform', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(3, 'alert', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(4, 'cctv', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(5, 'inspection-management', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(6, 'inspection-schedule', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(7, 'equipment-assets', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(8, 'inspection-report', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(9, 'permission-management', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO UPDATE SET
    permission_name = EXCLUDED.permission_name,
    updated_at = EXCLUDED.updated_at;

-- Reset permission sequence
SELECT setval('permission_id_seq', (SELECT MAX(id) FROM permission));

-- Insert role-permission mappings
-- Role 1 (管理员) has access to all permissions
INSERT INTO role_permission (role_id, permission_id, can_access, can_edit, created_at, updated_at)
VALUES
(1, 1, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 2, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 3, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 4, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 5, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 6, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 7, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 8, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(1, 9, true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
-- Role 2 (一般用户) has access to most permissions but not permission-management
(2, 1, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 2, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 3, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 4, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 5, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 6, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 7, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
(2, 8, true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Display summary
DO $$
DECLARE
    org_count INTEGER;
    role_count INTEGER;
    user_count INTEGER;
    perm_count INTEGER;
    role_perm_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO org_count FROM organization;
    SELECT COUNT(*) INTO role_count FROM role;
    SELECT COUNT(*) INTO user_count FROM "user";
    SELECT COUNT(*) INTO perm_count FROM permission;
    SELECT COUNT(*) INTO role_perm_count FROM role_permission;

    RAISE NOTICE '=== Migration Summary ===';
    RAISE NOTICE 'Organizations: %', org_count;
    RAISE NOTICE 'Roles: %', role_count;
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Permissions: %', perm_count;
    RAISE NOTICE 'Role-Permission mappings: %', role_perm_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Default users (username / base64_password):';
    RAISE NOTICE '  管理者 / 566h55CG6ICFMDAxQWRtaW4xMjNf';
    RAISE NOTICE '  superuser / c3VwZXJ1c2VyMTIzNDU2Nw==';
END $$;

-- 插入預設偵測規則
-- 可用的偵測類型: helmet, drowsiness, face, inactivity, custom

-- 1. 安全帽偵測規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'helmet-detection-all',
    '全域安全帽偵測',
    '偵測所有影像來源中未戴安全帽的人員，適用於工地、工廠等需要強制配戴安全帽的場所',
    true,
    NULL,  -- 適用於所有串流類型
    NULL,  -- 適用於所有串流來源
    NULL,  -- 適用於所有人員
    '["helmet"]',
    0.7,  -- 信心度閾值
    NULL,  -- 不需要時間閾值
    true,  -- 啟用通知
    '{"methods": ["api", "websocket"], "severity": "high"}',
    false,  -- 不啟用排程（全天候偵測）
    NULL,
    100,  -- 高優先級
    NOW(),
    NOW()
);

-- 2. 瞌睡偵測規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'drowsiness-detection-all',
    '全域瞌睡偵測',
    '偵測所有影像來源中打瞌睡的人員，適用於駕駛監控、值班人員監控等場景',
    true,
    NULL,
    NULL,
    NULL,
    '["drowsiness"]',
    0.6,  -- 瞌睡偵測使用較低的閾值
    3.0,  -- 持續3秒以上才觸發警報
    true,
    '{"methods": ["api", "websocket"], "severity": "critical"}',
    false,
    NULL,
    200,  -- 最高優先級
    NOW(),
    NOW()
);

-- 3. 人臉辨識規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'face-recognition-all',
    '全域人臉辨識',
    '辨識所有影像來源中的人臉，記錄已知人員並標記未知人員',
    true,
    NULL,
    NULL,
    NULL,
    '["face"]',
    0.6,  -- 人臉辨識閾值
    NULL,
    true,
    '{"methods": ["api", "websocket"], "severity": "medium", "unknown_only": false}',
    false,
    NULL,
    50,  -- 中等優先級
    NOW(),
    NOW()
);

-- 4. 未知人員警報規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'unknown-person-alert',
    '未知人員警報',
    '當偵測到未知人員時立即發送警報，適用於需要門禁管理的場所',
    true,
    NULL,
    NULL,
    NULL,
    '["face"]',
    0.5,
    NULL,
    true,
    '{"methods": ["api", "websocket"], "severity": "high", "unknown_only": true}',
    false,
    NULL,
    150,  -- 高優先級
    NOW(),
    NOW()
);

-- 5. 不活動偵測規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'inactivity-detection-all',
    '全域不活動偵測',
    '偵測影像中長時間無活動的情況，適用於監控區域是否有異常靜止狀態',
    true,
    NULL,
    NULL,
    NULL,
    '["inactivity"]',
    0.7,
    600.0,  -- 10分鐘無活動才觸發
    true,
    '{"methods": ["api", "websocket"], "severity": "medium"}',
    false,
    NULL,
    30,  -- 較低優先級
    NOW(),
    NOW()
);

-- 6. WEBCAM 專用綜合偵測規則
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'webcam-comprehensive',
    'WEBCAM 綜合偵測',
    '針對 WEBCAM 類型影像來源的綜合偵測，包含安全帽、瞌睡和人臉辨識',
    true,
    'WEBCAM',
    NULL,
    NULL,
    '["helmet", "drowsiness", "face"]',
    0.7,
    NULL,
    true,
    '{"methods": ["api", "websocket"], "severity": "high"}',
    false,
    NULL,
    120,  -- 高優先級
    NOW(),
    NOW()
);

-- 7. 工作時間安全帽偵測（帶排程）
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'helmet-work-hours',
    '工作時間安全帽偵測',
    '僅在工作時間（週一至週五 08:00-18:00）執行安全帽偵測',
    false,  -- 預設關閉，可依需求開啟
    NULL,
    NULL,
    NULL,
    '["helmet"]',
    0.7,
    NULL,
    true,
    '{"methods": ["api", "websocket"], "severity": "high"}',
    true,  -- 啟用排程
    '{"days": [1,2,3,4,5], "start_time": "08:00", "end_time": "18:00", "timezone": "Asia/Taipei"}',
    100,
    NOW(),
    NOW()
);

-- 8. 夜班瞌睡偵測（帶排程）
INSERT INTO detection_rules (
    rule_id,
    name,
    description,
    enabled,
    stream_source_type,
    stream_source_ids,
    person_ids,
    detection_types,
    confidence_threshold,
    time_threshold,
    notification_enabled,
    notification_config,
    schedule_enabled,
    schedule_config,
    priority,
    created_at,
    updated_at
) VALUES (
    'drowsiness-night-shift',
    '夜班瞌睡偵測',
    '針對夜班時段（22:00-06:00）加強瞌睡偵測',
    false,  -- 預設關閉
    NULL,
    NULL,
    NULL,
    '["drowsiness"]',
    0.5,  -- 較低閾值，更敏感
    2.0,  -- 持續2秒即觸發
    true,
    '{"methods": ["api", "websocket"], "severity": "critical"}',
    true,
    '{"days": [0,1,2,3,4,5,6], "start_time": "22:00", "end_time": "06:00", "timezone": "Asia/Taipei"}',
    200,
    NOW(),
    NOW()
);

-- 顯示插入結果
SELECT
    rule_id,
    name,
    enabled,
    detection_types,
    confidence_threshold,
    priority
FROM detection_rules
ORDER BY priority DESC;

-- NOTE: The `latest.timestamp` as 'timestamp' is a bit of a hack.
-- See: https://forum.newrelic.com/s/hubtopic/aAXPh0000008lZdOAI/timestamp-behavior-with-nested-aggregations
SELECT latest(`latest.timestamp`) as 'timestamp',
    latest(namespaceName) as 'namespaceName',
    sum(cpuUsedCores) as 'cpuUsedCores',
    sum(memoryUsedBytes) as 'memoryUsedBytes'
FROM (
    FROM K8sContainerSample
    SELECT latest(timestamp) as 'latest.timestamp',
        latest(namespaceName) as 'namespaceName',
        latest(podName) as 'podName',
        latest(cpuUsedCores) as 'cpuUsedCores',
        latest(memoryUsedBytes) as 'memoryUsedBytes'
    WHERE clusterName = '{{cluster_name}}'
    FACET entityId
    LIMIT MAX
)
FACET podName
LIMIT MAX
WITH TIMEZONE 'UTC'
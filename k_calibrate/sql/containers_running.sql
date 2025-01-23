-- TODO:
--  1. Does the `AND status in (...)` predicate alter results. Namely, if the timespan is 1 hour, and a container has been removed completely half way through that time period, will the old `Running` records be found and the container counted as running?
SELECT latest(status)
FROM K8sContainerSample
WHERE clusterName = '{{clusterName}}'
    AND namespaceName = '{{namespaceName}}'
    AND status = '{{status}}' -- TODO: Lists?
FACET entityId
SINCE {{since}}
- Always UTC time: https://docs.newrelic.com/docs/nrql/nrql-syntax-clauses-functions/#func-toTimestamp
- [Nested aggregations](https://docs.newrelic.com/docs/nrql/using-nrql/nested-aggregation-make-ordered-computations-single-query/) vs [Subqueries](https://docs.newrelic.com/docs/nrql/using-nrql/subqueries-in-nrql/)

### Nested query timestamp overriding

```SQL
SELECT *
FROM (
    FROM K8sContainerSample
    SELECT latest(timestamp) as 'latest.timestamp'
    LIMIT MAX
)
LIMIT MAX
```

Will produce the following:

![Two timestamp columns](../images/nested_timestamp_two.png)


```SQL
SELECT *
FROM (
    FROM K8sContainerSample
    SELECT latest(timestamp) as 'timestamp' -- Note how this is the same as the default timestamp column
    LIMIT MAX
)
LIMIT MAX
```

And New Relic will very happily replace your aggregated timestamp **(without warning)** with their own.

![One timestamp column with New Relic overrides](../images/nested_timestamp_override.png)

To this point, I have not been able to find any documentation in the [nested aggregation docs](https://docs.newrelic.com/docs/nrql/using-nrql/nested-aggregation-make-ordered-computations-single-query/) or otherwise on this behavior. I asked a forum question about this behavior so we will see: https://forum.newrelic.com/s/hubtopic/aAXPh0000008lZdOAI/timestamp-behavior-with-nested-aggregations
# New Relic Integration

The [New Relic Kubernetes Integration](https://github.com/newrelic/nri-kubernetes) provides a wholistic monitoring solution for Kubernetes clusters.

## Other notes

1. For some crashing containers, the `containerID` was `null` in new relic
2. Use of `entityId` / `entityType` instead of `containerID` ^
    - If you FACET over a null field nothing shows up for those NULL entities

### !!! Note !!!

1. Although a fair amount of research has gone into this writeup, it should not be considered an authoritative source of information.
2. This investigation was preformed on [version 3.32.2](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/) of the infrastructure.

The `controlplane` scraper has a [configurable kind](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/controlplane/daemonset.yaml#L3) where `DaemonSet` is the default. It is noted in the [values file](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/values.yaml#L238-L240) that this can be changed when users are using "static endpoints" to `Deployment` in order to avoid reporting metrics twice.

DaemonSet
- `controlplane`
    - `nri-kubernetes`
    - `k8s-events-forwarder`
- `kubelet`
    - `nri-kubernetes`
    - `infrastructure-bundle`
Deployments / ReplicaSet
- `ksm`
    - `nri-kubernetes`
    - `k8s-events-forwarder`

## Docker image / binary operation

There is one primary docker image [newrelic/nri-kubernetes](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/Dockerfile) for this project which, after using [tini](https://github.com/krallin/tini), will launch the `nri-kubernetes` command ([source](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/cmd/nri-kubernetes/main.go)). Interestingly, there are no command arguments or even commands associated with these containers (see [here](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/controlplane/daemonset.yaml#L68-L71), [here](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/ksm/deployment.yaml#L61-L64), and [here](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/kubelet/daemonset.yaml#L62-L65)). Not even a small argument to specify which type of scraper to run.

Instead configs are [mounted as files](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/controlplane/daemonset.yaml#L100-L103) and populated from [config map values](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/controlplane/daemonset.yaml#L171-L175) (see [reference](https://kubernetes.io/docs/concepts/storage/volumes/#configmap)). After constructing the configured scrappers, these scrappers will be [run in a infinite loop](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/cmd/nri-kubernetes/main.go#L156-L181) to continuously publish data.

### Publish timing

The timing of the loop is defined by the "interval" which is set on all config maps and defaults to 15 seconds (see [here](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/controlplane/scraper-configmap.yaml#L12) and [here](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/templates/_helpers.tpl#L84-L91)). There is more discussion of this `lowDataMode` parameter on the [newrelic documentation](https://docs.newrelic.com/docs/kubernetes-pixie/kubernetes-integration/installation/reduce-ingest/) in multiple places it is suggested to not have this interval exceed 40 seconds.

<!-- Note that if, for example, all three scrapers were active in a single binary, this interval would define the interval of all three combined. And since the control plane scraper is [run last](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/cmd/nri-kubernetes/main.go#L185-L208) it would have the most offset from the start time -->

## Control Plane Scraper

The control plane scraper contains a [configurable set of components](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/charts/newrelic-infrastructure/values.yaml#L265-L483): `Scheduler`, `Etcd`, `ControllerManager` and `APIServer`. These components are parsed during [scraper creation](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/controlplane/scraper.go#L79) with help of [this utility](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/controlplane/components.go#L34-L82). Each execution of the scraper, these components will be [turned into jobs](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/controlplane/scraper.go#L140-L167) which are subsequently executed.

### --- Notes on datasources names

The component which publishes data is the [IntegrationPopulator](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/definition/populate.go#L56). It handles the output of `Group(..)` operations and publishes that data. The component which decides the metric name to publish (`K8ClusterSample`, `K8PodSample`, etc) is called a [msTypeGuesser](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/definition/populate.go#L119-L130) and is set to [K8sMetricSetTypeGuesser](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/definition/guessfunc.go#L10-L16) by `scrape.Job.Populate`.

Interestingly, the population of `K8sClusterSample` seems to be [more hard coded](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/definition/populate.go#L19-L43). This is invoked on every call of `IntegrationPopulator` which has a [successful data push](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/src/definition/populate.go#L144-L149). It makes sense then for the **timing delta of records in this table to be smaller than the set interval**.

## Notes on debugging methods

To enable verbose logging on `nri-kubernetes` executions it is helpful to add the following to config maps such as `newrelic-bundle-nrk8s-controlplane` and kill the associated pod for a restart.

**NOTE:** Adding `verbose: true` did not seem to have an effect although there [appears to be support for this](https://github.com/newrelic/nri-kubernetes/blob/v3.32.2/cmd/nri-kubernetes/main.go#L65-L67) (user error?)

```yaml
   nri-kubernetes.yml: |-
     logLevel: "debug"
```

```bash
kubectl edit configmap newrelic-bundle-nrk8s-controlplane -n newrelic
```
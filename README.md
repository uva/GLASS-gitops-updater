GLASS-gitops-updater
=

The `GLASS-gitops-updater` provides an HTTP API for updating YAML files stored in a git-repository.
You can use this when you're using gitops software on your Kubernetes cluster like Argo CD or Flux.
It's compatible with both GitHub and GitLab and can also do some tricks when you want to deploy review apps.
Besides that, the provider Helm chart also helps you out when you want to store the needed tokens within an
Azure Key Vault.

Overview
-
Idea is simple: you provide configuration when you deploy the `GLASS-gitops-updater`, probably using the Helm values.
You can provide multiple configuration lines which are identified by a unique name.
Next to a name, every configuration line has a handler, a provider and some additional config (like a secret and path).
The chosen handler will determine the behaviour of your call.

Setup
-
Basically you need to install the provided Helm chart to a Kubernetes server to make the application available.
In the near future we will make the required Docker container and Helm chart publicly available. For now you need
to build it yourselves. You can do it, you're a great engineer!

For now, we will assume the updater is available somewhere on: `https://your-domain.com/gitops-updater`

GitHub provider
-
When configuring a GitHub provider, the configuration will look similar to the example below. You will need to create
a GitHub Personal Access Token (PAT) on the relevant settings page: https://github.com/settings/tokens

Make sure you grant sufficient permissions (`repo`) and make sure the PAT is available to the Docker container running
the `GLASS-gitops-updater` as a mounted file. You can achieve this by mounting a secret,
possibly using the Azure Key Vault.
```yaml
providers:
  - name: my-github-repo
    repository: example/repo
    branch: main
    type: GitHub
    tokenPath: /mnt/secrets/gitops-updater-github-token
```

Argo CD handler
-
When you configure a configuration line like below, you will be able to update an Argo CD YAML file.
```yaml
config:
  - name: example-name
    path: directory/manifest.yaml
    secretPath: /mnt/secrets/gitops-updater-secret
    handler: argocd
    provider: my-github-repo
```
Given this configuration, the GET-call that should be executed looks like this:
```sh
curl -s https://your-domain.com/gitops-updater?name=example-name&version=1.0.1&secret=very-secret
```
The `argocd`-handler will validate if the secret matches the secret provided in the configuration. After that
it will retrieve the file `directory/manifest.yaml` and expect a file that looks a bit like this:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: example-name
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: default

  source:
    repoURL: my-repository.com
    chart: my/chart
    targetRevision: 1.0.0

    helm:
      values: |
        some: value

  destination:
    server: https://kubernetes.default.svc
    namespace: some-namespace

  syncPolicy:
    automated:
      prune: true
    syncOptions:
    - CreateNamespace=true
```
Please note that the value of `metadata.name` should match the name of the configuration line. When the secret
matches, the file exists and the name matches, it will retrieve the current version (`1.0.0`) and to a semver-comparison.
Only when the requested version (`1.0.1`) is higher than the current one, it will perform a commit where it updates the version.
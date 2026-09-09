# IEPP L2 Azure Confidential VM experiment

Status: implementation and local negative tests complete; live Azure evidence is not claimed until the run below is
performed and its redacted result manifest is reviewed.

## What this experiment establishes

The L2 gate accepts an IEPP transition only when all of the following hold:

1. the IEPP Ed25519 transition signature and L1 state transition are valid;
2. the Microsoft Azure Attestation (MAA) JWT has a valid RS256 signature from the policy-pinned issuer;
3. the attested platform is an Azure-compliant AMD SEV-SNP VM with Secure Boot and vTPM enabled;
4. the hardware report's `user-data` digest binds the IEPP session, domain, challenge, predecessor, next counter,
   key identifier/public key, and runtime commitment;
5. the JWT is fresh under the local maximum-age policy;
6. the exact token is committed into the signed IEPP evidence.

The Ed25519 seed is sealed as a TPM `keyedhash` object under PCR policy `sha256:0,1,2,3,4,7`. It is never passed in a
command argument. A copied sealed object is expected to fail on the second VM because the TPM parent hierarchy differs.

This does **not** prove physical uniqueness, protect against a malicious/root guest after the key has been unsealed into
process memory, make one registry partition-safe, or turn a finite experiment into a general security proof.

## Cost and safety controls

- The template creates exactly two `Standard_DC2as_v5` Confidential VMs, two 30-GiB Standard SSD OS disks, two
  Standard public IPv4 addresses, one VNet, and one NSG.
- MAA itself does not require a separately deployed attestation provider for the shared regional endpoint.
- SSH is allowed only from the operator CIDR; passwords and all other inbound access are disabled.
- Every resource is placed in one dedicated resource group and tagged with `deleteAfterUtc`.
- The deployment script shows Azure account/SKU state, runs `what-if`, and requires the literal confirmation `DEPLOY`
  immediately before billable resources are created.
- The expiry tag is a reminder, not an automatic deletion mechanism. Always run the teardown and verify completion.

Check the current Azure price for the selected subscription/region immediately before deployment. Do not infer a final
charge from a documentation estimate: reservations, taxes, currency conversion, disk and IP billing can differ.

## Prerequisites

- Azure CLI authenticated to the intended subscription;
- permission to create and delete resource groups, network resources, and Confidential VMs;
- DCasv5 quota/capacity in Korea Central (or an explicitly reviewed alternative region);
- an OpenSSH key pair and the operator's current public IPv4 `/32` CIDR;
- Bash with GNU `date` for the helper scripts.

The Microsoft evidence collector is pinned to upstream commit
`d42eb2dad2335ab9e516bb69180a227d4a10f86c`; do not silently replace it during a reported run.

## Deploy

```bash
export IEPP_SSH_PUBLIC_KEY="$(< ~/.ssh/id_ed25519.pub)"
export IEPP_ADMIN_SOURCE_CIDR="203.0.113.10/32"
export IEPP_LOCATION="koreacentral"
export IEPP_RESOURCE_GROUP="iepp-l2-experiment"
bash deploy/azure/l2/deploy.sh
```

Keep the JSON deployment output. Wait until `/opt/iepp-l2/CLOUD_INIT_READY` exists on both nodes.

## Live positive test on each CVM

Use the `nodePublicIps` and `attestationIssuer` deployment outputs. On each node:

```bash
sudo /opt/iepp-l2/venv/bin/python \
  /opt/iepp-l2/iepp/reference/iepp_vnext/l2_live_smoke.py \
  --issuer https://sharedkrc.krc.attest.azure.net
```

Expected result: `CONTINUITY_VALID`. Store the printed result, not the raw JWT. The result includes only a JWT hash,
evidence ID, counter, and outcome.

## Cross-vTPM clone probe

Copy only node 1's sealed public/private blobs to a fresh directory on node 2. Do not copy any unsealed seed. Then run:

```bash
sudo /opt/iepp-l2/venv/bin/python \
  /opt/iepp-l2/iepp/reference/iepp_vnext/l2_live_smoke.py \
  --issuer https://sharedkrc.krc.attest.azure.net \
  --key-directory /var/lib/iepp-l2/copied-node-1-key \
  --unseal-only
```

Expected result: `REJECTED`. `UNEXPECTED_SUCCESS` is a stop condition and must be reported as a failed security test.

## Deterministic attack suite

Run on either node or locally:

```bash
python -m unittest reference/iepp_vnext/tests/test_l2_attestation.py -v
```

The suite covers signature tampering, token substitution, wrong issuer/`jku`, stale token, wrong hardware binding,
non-compliant platform, missing Secure Boot/vTPM, token reuse across challenges, and an attested two-candidate fork race.
Synthetic test JWTs validate verifier logic; only the live smoke test supplies hardware evidence.

## Teardown and charge verification

After collecting the results:

```bash
bash deploy/azure/l2/destroy.sh
az group exists --name iepp-l2-experiment
```

The final command must eventually print `false`. Then inspect Azure Cost Management for residual disk, IP, backup, or
logging resources before considering the experiment closed.

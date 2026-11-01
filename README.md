# Strata Cloud Manager Terraform object inventory

This workspace provisions a tenant-safe SCM object inventory using the Palo Alto Networks SCM Terraform provider. The current design intentionally focuses on the working object layers that were validated in this environment:

- tag objects
- address objects
- address groups
- service objects
- service groups

Security policy and rule resources have been intentionally excluded from the active project because SCM tenant validation is stricter than a generic starter configuration and requires real zone names, policy types, and valid object references.

## Supported object types

The project is driven from CSV files in the `data/` directory and is assembled in `main.tf`.

### 1. Tag objects

The `data/tags.csv` file creates SCM tag objects that can be used to classify address objects and other inventory entries.

Columns:

- `name`
- `color`

Example:

```csv
name,color
prod,Red
dmz,Blue
web,Green
```

### 2. Address objects

The `data/addresses.csv` file supports SCM address entries with the following fields:

- `name`
- `kind`
- `value`
- `description`
- `tags`

Allowed `kind` values for `scm_address` in this project are:

- `ip_netmask`
- `ip_range`
- `ip_wildcard`
- `fqdn`

The `tags` field is optional. If you use it, each tag value must match a real SCM tag object that already exists in the tenant; otherwise SCM rejects the object as an invalid reference.

Example:

```csv
name,kind,value,description,tags
corp-dmz-web-01,ip_netmask,10.20.10.11/32,Production DMZ web frontend,
corp-vpn-gateway,fqdn,vpn-gateway.example.com,VPN gateway endpoint,
```

### 2. Address groups

The `data/address_groups.csv` file defines static groups of address objects.

Columns:

- `name`
- `description`
- `members`

Example:

```csv
name,description,members
corp-web-tier,Production web tier members,"corp-dmz-web-01,corp-dmz-web-02,corp-app-01"
```

### 3. Service objects

The `data/services.csv` file creates SCM service objects. Supported service entries are built as protocol-specific objects with a single port value.

Columns:

- `name`
- `protocol`
- `port`
- `description`

Protocol examples:

- `tcp`
- `udp`

Example:

```csv
name,protocol,port,description
corp-web-https,tcp,443,HTTPS web service
corp-ldap-udp,udp,389,LDAP directory access
```

### 4. Service groups

The `data/service_groups.csv` file defines static groups of service objects.

Columns:

- `name`
- `members`

Example:

```csv
name,members
corp-web-services,"corp-web-https,corp-web-http"
```

## Administrator accounts

This project no longer includes the administrator module or the Terraform-local-user flow. The administrator management path has been removed from the active project because the SCM admin model exposed by the API is not represented correctly in the provider/resource surface used here.

The supported automation in this repo is intentionally limited to inventory objects and services:

- tags
- address objects
- address groups
- service objects
- service groups

If you need SCM admin creation, treat it as a separate manual or API-only workflow outside this Terraform inventory project.

## Folder selection

This project uses the `folder` variable from `variables.tf`.

For this tenant pattern, the current default is:

```hcl
folder = "All"
```

In some tenants the correct value may instead be `Global` or another folder name. Update `terraform.tfvars` or the exported Terraform variable to match your SCM tenant.

## Required Terraform variables

Create or update `terraform.tfvars` with values similar to:

```hcl
scm_host = "api.sase.paloaltonetworks.com"
client_id = "<your-client-id>"
client_secret = "<your-client-secret>"
tsg_id = "<your-tsg-id>"
folder = "All"
```

## Using your existing `.env` file

If your Python automation already stores the credentials in a `.env` file, you can pass them into Terraform without duplication:

```bash
export TF_VAR_client_id="$(grep '^SCM_CLIENT_ID=' .env | cut -d= -f2-)"
export TF_VAR_client_secret="$(grep '^SCM_CLIENT_SECRET=' .env | cut -d= -f2-)"
export TF_VAR_tsg_id="$(grep '^SCM_TSG_ID=' .env | cut -d= -f2-)"
export TF_VAR_folder="All"
terraform init
terraform plan
terraform apply
```

## Typical workflow

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

## Files you will usually edit

- `data/addresses.csv` — address objects
- `data/address_groups.csv` — address group membership
- `data/services.csv` — service objects
- `data/service_groups.csv` — service group membership
- `terraform.tfvars` — SCM credentials and folder name

## Notes

- Keep `terraform.tfvars` local and do not commit it.
- The CSV format intentionally uses comma-separated members and tag values to match the current Terraform logic in `main.tf`.
- If you later add rule-based policy objects, confirm the tenant's actual zone names and policy types before enabling that layer.

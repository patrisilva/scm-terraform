# Strata Cloud Manager Terraform object inventory

This workspace provisions a tenant-safe SCM object inventory using the Palo Alto Networks SCM Terraform provider. The current design intentionally focuses on the working object layers that were validated in this environment:

- tag objects
- address objects
- address groups
- service objects
- service groups

Security policy imports are now supported through a flat file naming model under `data/security policies`. Each SCM folder gets a pair of files named `Folder_pre-rules.csv` and `Folder_post-rules.csv`, which makes the tenant structure easier to manage and easier to scan.

Example hierarchy:

```text
data/
  objects/
    addresses.csv
    tags.csv
  object_groups/
    address_groups.csv
  services/
    services.csv
  service_groups/
    service_groups.csv
  security policies/
    Global_pre-rules.csv
    Global_post-rules.csv
    All_pre-rules.csv
    All_post-rules.csv
    FNM_pre-rules.csv
    FNM_post-rules.csv
    LAB_pre-rules.csv
    LAB_post-rules.csv
```

This keeps the rule files aligned to the actual tenant folders: `Global`, `All`, `FNM`, and `LAB`. In the SCM provider, `Global` is not a valid security-rule folder value; the rule loader maps it to `All` for policy creation while keeping the CSV file names readable and tenant-native.

## Supported object types

The project is driven from CSV files in the `data/` directory and is assembled in `main.tf`.

### 1. Tag objects

The `data/objects/tags.csv` file creates SCM tag objects that can be used to classify address objects and other inventory entries.

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

The `data/objects/addresses.csv` file supports SCM address entries with the following fields:

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

The `data/object_groups/address_groups.csv` file defines static groups of address objects.

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

The `data/services/services.csv` file creates SCM service objects. Supported service entries are built as protocol-specific objects with a single port value.

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

The `data/service_groups/service_groups.csv` file defines static groups of service objects.

Columns:

- `name`
- `members`

Example:

```csv
name,members
corp-web-services,"corp-web-https,corp-web-http"
```

### 5. Folder-scoped security rules

The project also supports SCM security rules loaded from CSV files under `data/security policies`. Rules are grouped by folder and by rule position, with one pair of files per SCM folder:

- `Global_pre-rules.csv`
- `Global_post-rules.csv`
- `All_pre-rules.csv`
- `All_post-rules.csv`
- `FNM_pre-rules.csv`
- `FNM_post-rules.csv`
- `Lab_pre-rules.csv`
- `Lab_post-rules.csv`

The file naming convention is intentionally `Folder_pre-rules.csv` and `Folder_post-rules.csv`, which makes it easier to match each CSV to the SCM folder directly.

Required columns for each rule row are:

- `name`
- `description`
- `action`
- `from` (source zone; also accepts `source zone`)
- `to` (destination zone; also accepts `destination zone`)
- `source` (source addresses; also accepts `source addresses`)
- `destination` (destination addresses; also accepts `destination addresses`)
- `category` (rule category, for example `any` or a valid SCM category reference)
- `application`
- `service` (use an SCM service object name like `corp-ssh`, not a raw keyword such as `ssh`)
- `source_user` (source users; also accepts `source users`)
- `log_end`
- `disabled`
- `URL Category` (maps to the SCM API `category` array; use a valid URL category string such as `any` or a tenant-approved category name)

The CSV layer supports multiple values in the list-based fields. `from`, `to`, `source`, `destination`, `application`, `service`, `source_user`, and `URL Category` all accept comma-separated values in a single CSV cell, and the Terraform conversion logic splits them into SCM lists before creating the rule.

Optional columns supported for ordering and CSV compatibility:

- `relative_position`
- `target_rule`
- `policy_type`
- `url_category`
- `profile_group`

The rule builder maps the CSV data into the provider-supported list fields and profile setting structure used by the SCM security-rule resource.

Example:

```csv
name,description,action,from,to,source,destination,application,service,source_user,URL Category,profile_group,log_end,disabled
allow-web-traffic,Allow HTTPS and DNS from trust to untrust,trust,untrust,corp-web-tier,corp-web-tier,web-browsing,dns,any,financial-services,best-practice,true,false
allow-lab-fnm-ops,Allow lab traffic in the LAB folder,ELAN,WAN,N-10.1.10.0_24,any,"web-browsing,ssl",application-default,any,financial-services,best-practice,true,false
```

Rules are processed by the folder name encoded in the file itself; the `folder` variable remains for the object inventory layer, while `*_pre-rules.csv` and `*_post-rules.csv` define the policy scope.

## Administrator accounts

This project no longer includes the administrator module or the Terraform-local-user flow. The administrator management path has been removed from the active project because the SCM admin model exposed by the API is not represented correctly in the provider/resource surface used here.

The supported automation in this repo includes the working inventory objects plus folder-aware security rule imports:

- tags
- address objects
- address groups
- service objects
- service groups
- security rules by folder and pre/post position

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

- `data/objects/addresses.csv` — address objects
- `data/objects/tags.csv` — tag objects
- `data/object_groups/address_groups.csv` — address group membership
- `data/services/services.csv` — service objects
- `data/service_groups/service_groups.csv` — service group membership
- `data/security policies/Global/pre-rules.csv` and `data/security policies/Global/post-rules.csv` — security rules for the Global folder
- `data/security policies/Global/All/pre-rules.csv` and `data/security policies/Global/All/post-rules.csv` — security rules for the All folder nested under Global
- `data/security policies/Global/FNM/LAB/pre-rules.csv` and `data/security policies/Global/FNM/LAB/post-rules.csv` — security rules for the nested LAB folder under FNM
- `terraform.tfvars` — SCM credentials and folder name

## Notes

- Keep `terraform.tfvars` local and do not commit it.
- The CSV format intentionally uses comma-separated members and tag values to match the current Terraform logic in `main.tf`.
- If you later add rule-based policy objects, confirm the tenant's actual zone names and policy types before enabling that layer.

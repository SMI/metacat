# Metacat

This repository contains documents and scripts for the creation of a custom medical imaging metadata catalogue. This includes the following processes:

- Statistical metadata generation at different stages of the SMI pipeline (raw, staging, live)
- Derived metadata generation from DICOM metadata (e.g., DICOM-metadata based classification by body part)
- Import of [DICOM standard metadata](https://github.com/innolitics/dicom-standard)
- Creation of visualisations based on generated metadata via a web interface

## Repo contents

| Directory | Contents |
| --------- | -------- |
| [docs](./docs) | Metadata and table schemas, overview of the data architecture. |
| [metadata_collection](./metadata_collection) | Scripts for the generation and collection of statistical metadata and storage in a MongoDB database. |
| [metadata_studies](./metadata_studies) | Derived metadata studies and experiments, including scripts for extracting metadata for analysis. |
| [catalogue_ui](./catalogue_ui) | Implementation of Flask app as the catalogue UI. |
| [modules](./modules) | Shared document and database manipulation. |
| [test](./test) | Test deployment of all components in a Docker environment. |

## Deploy with Docker

If you want to change configuration (i.e., front-end serving port, database credentials), source an environment file like [config.env](./test/config.env) before the docker-compose command:

```shell
$ source test/config.env
$ docker-compose -f test/docker-compose.yml up
```

Otherwise, the default values from the compose file will be used.

This will launch the following containers:

- `smi-mariadb`: acting as both staging and live database
- `smi-mongodb`: acting as raw and metadata database
- `smi-catalogue`: host of catalogue front and back end

And will perform the following tasks:

1. Install [requirements.txt](./requirements.txt) and custom modules in the `smi-catalogue` container.
1. Make use of the [DICOM metadata schema](./docs/general_doc_schema.json) to generate synthetic documents in a `dicom` database on `smi-mongodb`.
1. Make use of the [table schema](./docs/general_table_schema.jinjasql) to create tables on `smi-mariadb` and populate them with data from the `dicom` MongoDB database. To emulate the processed data on the live system, two databases are populated, `data_load2` representing the `staging` database, and `smi` representing the `live` database.
1. Perform metadata collection tasks (see [documentation](./metadata_collection/README.md) for more details).
1. Run body part labelling (see [documentation](./metadata_studies/body_part_labelling/README.md) for more details).
1. Deploy catalogue UI.

You can manually re-run any of these tasks from the `smi-catalogue` container. For example:

```shell
(smi-catalogue) # . /home/metacat/test/config.env
(smi-catalogue) # cd /home/metacat/metadata_collection
(smi-catalogue) # python3 populate_catalogue.py -d dicom -i -l logs/
```

And you can manually analyse the MongoDB documents. If you used the default configuration, note that the username password are in the [config.env](./test/config.env) file:

```shell
(smi-mongodb) # mongosh -u <MONGOUSER> -p
<MONGOPASS>
```

Similarly for the MariaDB container:

```shell
(smi-mariadb) # mariadb -u <MYSQLUSER> -p
<MYSQLPASS>
```

To stop containers, just press CTRL+C and run the following command to clean up:

```shell
$ docker-compose -f ./test/docker-compose.yml down
```

'''Library class that holds general Mongo database-related functionality.
'''
import os
import logging
from typing import List, Dict, Union
import pymongo


# pylint: disable=R0904
class MongoLib:
    '''Class handling MongoDB connection and querying.
    '''
    def __init__(self, log):
        self.client = None
        self.db = None
        self.db_name = ''

        logging.getLogger(log)
        self.connect()

    def connect(self) -> None:
        '''Connect to MongoDB database based on credentials
        available via env vars.
        '''
        try:
            self.client = pymongo.MongoClient(
                os.environ.get("MONGOHOST"),
                username=os.environ.get("MONGOUSER"),
                password=os.environ.get("MONGOPASS"),
                authSource=os.environ.get("MONGOAUTHDB")
            )
            logging.info("Successful connection to database.")
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.error("Failed connection to database: %s.", error)
            raise error

    def switch_db(self, db_name: str) -> None:
        '''Connects to specified database.

        Args:
            db_name (str): Database name.
        '''
        try:
            self.db = self.client[db_name]
            self.db_name = db_name
            logging.info("Using database %s.", self.db_name)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.error("Failed database %s use: %s.", self.db_name, error)
            raise error

    def create_collection(self, collection: str) -> None:
        '''Creates a collection in the current database.

        Args:
            collection (str): Collection name.
        '''
        try:
            self.db[collection]
            logging.info("%s: Successfully created collection %s.",
                         self.db_name, collection)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed creating collection %s: %s",
                              self.db_name, collection, error)
            raise error

    def create_index(self, collection: str, index: str,
                     uniq: bool = False) -> None:
        '''Creates an index in a given collection.

        Args:
            collection (str): Collection name.
            index (str): Index name.
            uniq (bool, optional): Whether the index is unique.
                                   Defaults to False.
        '''
        try:
            self.db[collection].create_index(
                [(index, pymongo.ASCENDING)],
                unique=uniq
            )
            logging.info("%s: Successfully created an index for %s in %s",
                         self.db_name, index, collection)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed creating index %s in %s: %s",
                              self.db_name, index, collection, error)
            raise error

    def list_collections(self) -> List[str]:
        '''Lists collections in current database.

        Raises:
            error: PyMongo error on list_collection_names().

        Returns:
            List: List of collections in the current database.
        '''
        try:
            collections = sorted(list(self.db.list_collection_names()))
            logging.info("%s: Successfully extracted collections", self.db_name)
            return collections
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed extracting collections: %s",
                              self.db_name, error)
            raise error

    def sample(self, collection: str, number: int) -> List[Dict]:
        '''Finds and returns a given number of sample documents in a
           given collection.

        Args:
            collection (str): Collection name.
            number (int): Number of documents/samples.

        Raises:
            error: PyMongo error on aggregate.

        Returns:
            List[Dict]: List of Mongo documents.
        '''
        query = [
            {"$sample": {"size": number}}
        ]

        try:
            samples = self.db[collection].aggregate(query)
            logging.info(("%s: Successfully extracted %s sample document(s) "
                          "from collection %s"), self.db_name, number, collection)
            return list(samples)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting %s sample document(s) "
                               "from collection %s: %s"), self.db_name, number,
                              collection, error)
            raise error

    def search(self, collection: str, condition: Dict = None, selection: Dict = None) -> Dict:
        '''Finds and returns all documents in a given collection.

        Args:
            collection (str): Collection name.
            condition (Dict): Search condition.
            selection (Dict): Attribute selection, will be added to the query
                              after the condition.

        Raises:
            error: PyMongo Error on find().

        Returns:
            Dict: Mongo document.
        '''
        try:
            if condition is not None:
                if selection:
                    doc = self.db[collection].find(condition, selection)
                else:
                    doc = self.db[collection].find(condition)
            else:
                doc = self.db[collection].find()

            logging.info("%s: Successfully searched for %s in %s",
                         self.db_name, condition, collection)
            return doc
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed finding all documents in collection "
                              "%s: %s"), self.db_name, collection, error)
            raise error

    def count_images(self, collection: str):
        '''Counts the number of documents in a collection.

        Args:
            collection (str): Collection name.

        Raises:
            error: PyMongo error on count_documents().

        Returns:
            List: List of indexes.
        '''
        try:
            if collection == "series":
                query = [{"$group": {"_id": "$Modality", "count": {"$sum": "$header.ImagesInSeries"}}}]
                count = self.db[collection].aggregate(query)
            else:
                count = self.db[collection].count_documents({})

            logging.info("%s: Successfully counted documents in %s",
                         self.db_name, collection)
            return count
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed counting documents in %s: %s",
                              self.db_name, collection, error)
            raise error

    def get_modality_meta(self, modality: str) -> Union[List, Dict]:
        '''Returns metadata for a given modality.

        Args:
            modality (str): Modality name.

        Raises:
            error: PyMongo error on find_one().

        Returns:
            Dict: Modality metadata Mongo document.
        '''
        metadata: Union[List, Dict]

        try:
            if modality == "all":
                metadata = list(self.db["modalities"].find())
            else:
                metadata = dict(self.db["modalities"].find_one(
                    {"modality": modality}
                ))

            logging.info(("%s: Successfully extracted modality metadata for "
                          "modality %s"), self.db_name, modality)
            return metadata
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting modality metadata for "
                               "modality %s: %s"), self.db_name, modality,
                              error)
            raise error

    def get_tag_meta(self, modality: str) -> List[Dict]:
        '''Returns metadata of all tags belonging to the given modality.

        Args:
            modality (str): Modality name.
            standard (str, optional): Standard or proprietary.
                                      Defaults to "true" = standard.

        Raises:
            error: PyMongo error on find query.

        Returns:
            List[Dict]: List of tag metadata Mongo documents.
        '''
        try:
            if modality == "all":
                metadata = self.db["tags"].find()
            else:
                metadata = self.db["tags"].find(
                    {"modalities": {"$in": [modality]}}
                )

            logging.info(("%s: Successfully extracted tag metadata for "
                          "modality %s"), self.db_name, modality)
            return list(metadata)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting tag metadata for "
                               "modality %s: %s"), self.db_name, modality,
                              error)
            raise error

    def get_tag_public_status(self, tag: str) -> bool:
        '''Returns a tag's public status.

        Args:
            tag (str): Tag name.

        Raises:
            error: PyMongo error on find query.

        Returns:
            bool: True|False.
        '''
        try:
            status = self.db["tags"].find(
                {"tag": tag},
                {"public": 1, "_id": 0}
            )

            if status:
                status = list(status)[0]["public"]
                status = True if status == "true" else False

            logging.info("%s: Successfully extracted public status for tag %s",
                         self.db_name, tag)
            return status
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting public status for tag "
                               "%s: %s"), self.db_name, tag, error)
            raise error

    def list_fields(self, collection: str) -> List[Dict]:
        '''Returns a list of distinct fields in a given collection by modality.
           note, this only gives a list of all level 1 fields.

        Args:
            collection (str): Collection name.

        Raises:
            error: pymongo error on aggregate.

        Returns:
            list[dict]: [{"modality": <modality>,
                          "tags": [<tag_name>]
                        }]
        '''
        query = [
            {"$project": {
                "modality": "$Modality",
                "arrayofkeyvalue": {"$objectToArray": "$$ROOT"}
            }},
            {"$unwind": "$arrayofkeyvalue"},
            {"$group": {
                "_id": "$modality",
                "tag_list": {"$addToSet": "$arrayofkeyvalue.k"}
            }},
            {"$project": {
                "_id": 0,
                "modality": "$_id",
                "tags": "$tag_list"
            }}
        ]

        try:
            result = self.db[collection].aggregate(query, allowDiskUse=True)
            logging.info("%s: Successfully retrieved a list of fields from %s",
                         self.db_name, collection)
            return list(result)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed retrieving a list of fields from "
                               "%s: %s"), self.db_name, collection, error)
            raise error

    def get_field_values(self, collection: str, field: str, count: bool = False) -> List:
        '''Returns list of distinct values in given field.

        Args:
            collection (str): Collection name.
            field (str): Field name.
            count (bool): Frequency count. Default to False.

        Raises:
            error: PyMongo error on distinct().

        Returns:
            List: List of values.
        '''
        try:
            if count:
                query = [{"$sortByCount": f"${field}"}]
                values = self.db[collection].aggregate(query, allowDiskUse=True)
            else:
                values = self.db[collection].distinct(field)

            logging.info(("%s: Successfully extracted %s values from "
                          "collection %s"), self.db_name, field, collection)
            return list(values)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting %s values from "
                               "collection %s: %s"), self.db_name, field,
                              collection, error)
            raise error

    def insert_many(self, collection: str, docs: List[Dict]) -> None:
        '''Bulk-insert docs into collection.

        Args:
            collection (str): Collection name.
            docs (List[Dict]): List of dictionaries.

        Raises:
            error: PyMongo error on insert_many().
        '''
        try:
            self.db[collection].insert_many(docs)
            logging.info("%s: Successful bulk-insert of %s documents into %s",
                         self.db_name, len(docs), collection)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed bulk-insert into %s: %s",
                              self.db_name, collection, error)
            raise error

    def update_mod_tag_quality(self, modality: str, tag: Dict, collection: str = "modalities") -> None:
        '''Update a modality's tag. Subdocument update.

        Args:
            modality (str): Modality name.
            tag [Dict]: Tag metadata.

        Raises:
            error: PyMongo error on update_one().
        '''
        try:
            tag_set = {f"tags.$.{key}": value for key, value in tag.items()}

            query = {"modality": modality, "tags.tag": tag["tag"]}
            update = {"$set": tag_set}

            self.db[collection].update_one(query, update)
            logging.debug("%s: Successful update of tag %s for modality %s.",
                          self.db_name, tag["tag"], modality)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed update of tag %s for modality %s: %s",
                              self.db_name, tag["tag"], modality, error)
            raise error

    def upsert_modalities(self, modalities: List[Dict], collection: str = "modalities") -> None:
        '''Upsert modalities to collection modalities. If the modality exists,
           update, if it does not, insert.

        Args:
            modalities (List[Dict]): List of modality dictionaries.

        Raises:
            error: PyMongo error on update_one().
        '''
        logging.info("Upserting modalities...")

        for modality in modalities:
            try:
                mod_name = modality["modality"]
                query = {"modality": mod_name}
                update = {"$set": modality}

                self.db[collection].update_one(query, update, upsert=True)
                logging.debug("%s: Successful upsert of modality %s.",
                              self.db_name, mod_name)
            except (Exception, pymongo.errors.PyMongoError) as error:
                logging.exception("%s: Failed upsert of modality %s: %s",
                                  self.db_name, mod_name, error)
                raise error

    def upsert_tags(self, tags: List[Dict], collection: str = "tags") -> None:
        '''Upsert tags to collection tags. If the tag exists, update, if it
           does not, insert.

        Args:
            tags (List[Dict]): List of tag dictionaries.

        Raises:
            error: PyMongo error on update_one().
        '''
        logging.info("Upserting tags...")

        for tag in tags:
            try:
                query = {"tag": tag["tag"]}
                update = {"$set": tag}

                self.db[collection].update_one(query, update, upsert=True)
                logging.debug("%s: Successful upsert of tag %s to %s.",
                              self.db_name, tag, collection)
            except (Exception, pymongo.errors.PyMongoError) as error:
                logging.exception("%s: Failed upsert of tag %s to %s.",
                                  self.db_name, tag, collection)
                raise error

    def upsert_obj(self, obj: Dict, collection: str, condition, update) -> None:
        '''Upsert tags to collection tags. If the tag exists, update, if it
           does not, insert.

        Args:
            tags (List[Dict]): List of tag dictionaries.

        Raises:
            error: PyMongo error on update_one().
        '''
        logging.info("Upserting...")

        try:
            self.db[collection].update_one(condition, update, upsert=True)
            logging.debug("%s: Successful upsert to %s.",
                           self.db_name, collection)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed upsert to %s.",
                              self.db_name, collection)
            raise error

    def get_tag_quality(self, collection: str, tag: str) -> List:
        '''Returns the number of documents in a given collection that
           have a given tag.

        Args:
            collection (str): Collection name.
            tag (str): Tag name.

        Raises:
            error: PyMongo Error on find_one().

        Returns:
            List: [{"_id": "<MODALITY>", "exists": <NUMBER>, "emptyStr": <NUMBER>}]
        '''
        query = [
            {"$group": {
                "_id": "$Modality",
                "exists": {
                    "$sum": {"$cond": [f"${tag}", "$header.ImagesInSeries", 0]}
                },
                "emptyStr": {
                    "$sum": {"$cond": [{"$eq": [f"${tag}", ""]}, "$header.ImagesInSeries", 0]}
                }
            }}
        ]

        try:
            count = self.db[collection].aggregate(query, allowDiskUse=True)
            logging.info("%s: Successfully extracted tag qualty of %s from %s",
                         self.db_name, tag, collection)
            return list(count)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception(("%s: Failed extracting tag quality of %s from "
                               "%s: %s"), self.db_name, tag, collection, error)
            raise error

    def run_facet(self, collection: str, facet) -> List:
        '''Runs a given facet.

        Args:
            collection (str): Collection name.
            facet (_type_): Dictionary of queries to run as facet.

        Raises:
            error: PyMongo Error on aggregate.

        Returns:
            List: Depends on the structure of the facet.
        '''
        query = [{"$facet": facet}]

        try:
            logging.info("%s: Running facet query on %s", self.db_name,
                         collection)
            results = self.db[collection].aggregate(query, allowDiskUse=True)
            logging.info("%s: Successfully ran facet query on %s", self.db_name,
                         collection)

            return list(results)
        except (Exception, pymongo.errors.PyMongoError) as error:
            logging.exception("%s: Failed running facet query on %s: %s",
                              self.db_name, collection, error)
            raise error

    def disconnect(self) -> None:
        '''Disconnect from the database.
        '''
        if self.client is not None:
            self.client.close()
            logging.info("Successful disconnection from %s", self.db_name)

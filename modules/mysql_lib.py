'''Library class that holds relational database-related functionality.
'''
import os
import logging
from typing import List, Tuple
import mysql.connector as mysql


class MySQLib:
    '''Class handling relational database connection and querying.
    '''
    def __init__(self, log):
        self.conn = None
        self.db = None

        logging.getLogger(log)
        self.connect()
        self.cur = self.conn.cursor()

    def connect(self):
        '''Connect to relational database based on credentials available via
        env vars.
        '''
        try:
            self.conn = mysql.connect(
                user=os.environ.get("MYSQLUSER"),
                password=os.environ.get("MYSQLPASS"),
                host=os.environ.get("MYSQLHOST")
            )
            logging.info("Successful connection to database.")
        except mysql.Error as error:
            logging.exception("Failed connection to database: %s.", error)
            raise error

    def use_db(self, db_name: str) -> None:
        '''Uses a specified database.

        Args:
            db_name (str): Database name.

        Raises:
            error: Mysql error on USE.
        '''
        try:
            self.cur.execute(f"USE {db_name};")
            self.db = db_name
            logging.info("Using database %s.", db_name)
        except mysql.Error as error:
            logging.exception("Failed database %s use: %s", db_name, error)
            raise error

    def execute_query(self, query: str, values: Tuple = ()) -> None:
        '''Executes a given query.

        Args:
            query (str): Query string.

        Raises:
            error: Mysql error on query.
        '''
        try:
            if values:
                self.cur.execute(query, values)
                logging.info("%s: Executed query %s with values %s.",
                             self.db, query, values)
            else:
                self.cur.execute(query)
                logging.info("Executed query %s.", query)

            self.conn.commit()
        except mysql.Error as error:
            logging.exception("%s: Failed executing query %s: %s",
                              self.db, query, error)
            raise error

    def list_tables(self) -> List[Tuple]:
        '''Returns a list of tables in the current database.

        Raises:
            error: Mysql error on SHOW TABLES.

        Returns:
            List[Tuple]: [(<TABLE_NAME>,), (<TABLE_NAME>,)]
        '''
        try:
            self.cur.execute("SHOW TABLES;")
            tables = self.cur.fetchall()

            logging.info("%s: Successfully listed tables.", self.db)
            return tables
        except mysql.Error as error:
            logging.exception("%s: Failed listing tables: %s", self.db, error)
            raise error

    def list_table_columns(self, table: str) -> List[Tuple]:
        '''Retrieves a given table's columns.

        Args:
            table (str): Table name.

        Raises:
            error: Mysql error on SHOW COLUMNS FROM.

        Returns:
            List[Tuple]: [(<COLUMN_NAME>, <TYPE>, <UNIQUE>, <KEY>, <>, <>)]
        '''
        try:
            self.cur.execute(f"SHOW COLUMNS FROM {table};")
            columns = self.cur.fetchall()

            logging.info("%s: Successfully listed columns for table %s.",
                         self.db, table)
            return columns
        except mysql.Error as error:
            logging.exception("%s: Failed retrieving columns for table %s: %s",
                              self.db, table, error)
            raise error

    def count_table(self, table: str) -> int:
        '''Returns the number of records in a table.

        Args:
            table (str): Table name.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of rows in table.
        '''
        try:
            self.cur.execute(f"SELECT COUNT(*) FROM {table};")
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: Table %s has %s records.", self.db, table, counts)
            return counts
        except mysql.Error as error:
            logging.exception("%s: Failed counting records for table %s: %s",
                              self.db, table, error)
            raise error

    def count_aggregate_table(self, table: str) -> int:
        '''Returns the number of original + derived images from an
           aggregate image table.

        Args:
            table (str): Table name.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of rows in table.
        '''
        try:
            self.cur.execute(f"SELECT SUM(ORIGINAL + DERIVED) FROM {table};")
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: Aggregate table %s has %s images.",
                         self.db, table, counts)
            return counts
        except mysql.Error as error:
            logging.exception("%s: Failed counting images for table %s: %s",
                              self.db, table, error)
            raise error

    def count_sr_table(self, column: str) -> int:
        '''Returns the number of rows in a table.

        Args:
            column (str): Column on which the count to be performed.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of rows in table.
        '''
        try:
            self.cur.execute(f"SELECT COUNT(DISTINCT {column}) "
                             "FROM SR_ImageTable;")
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: Table SR_ImageTable has %s rows.", self.db,
                         counts)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting records for table "
                              "SR_ImageTable: %s"), self.db, error)
            raise error

    def count_studies_per_month(self, modality: str) -> List[Tuple]:
        '''Returns the number of studies per month by modality.

        Args:
            modality (str): Modality name.

        Raises:
            error: Mysql error on SELECT.

        Returns:
            List[Tuple]: [(<YYYY/MM>, <COUNT>)]
        '''
        try:
            query = ("SELECT CONCAT(YEAR(StudyDate), '/', MONTH(StudyDate)) "
                     "AS StudyMonth, COUNT(StudyInstanceUID) FROM "
                     f"{modality}_StudyTable GROUP BY StudyMonth;")

            self.cur.execute(query)
            counts = self.cur.fetchall()

            logging.info(("%s: Successfully counted studies per month for "
                          "modality %s."), self.db, modality)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting studies per month for "
                               "modality %s: %s"), self.db, modality, error)
            raise error

    def count_series_per_month(self, modality: str) -> List[Tuple]:
        '''Returns the number of series per month by modality.

        Args:
            modality (str): Modality name.

        Raises:
            error: Mysql error on SELECT.

        Returns:
            List[Tuple]: [(<YYYY/MM>, <COUNT>)]
        '''
        try:
            query = (("SELECT CONCAT(YEAR(StudyDate), '/', MONTH(StudyDate)) "
                      "AS StudyMonth, COUNT(Se.SeriesInstanceUID) "
                      f"FROM {modality}_StudyTable St "
                      f"INNER JOIN {modality}_SeriesTable Se "
                      "ON Se.StudyInstanceUID = St.StudyInstanceUID "
                      "GROUP BY StudyMonth;"))

            self.cur.execute(query)
            counts = self.cur.fetchall()

            logging.info(("%s: Successfully counted series per month for "
                          "modality %s."), self.db, modality)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting series per month for "
                               "modality %s: %s"), self.db, modality, error)
            raise error

    def count_images_per_month(self, modality: str) -> List[Tuple]:
        '''Returns the number of images per month by modality.

        Args:
            modality (str): Modality name.

        Raises:
            error: Mysql error on SELECT.

        Returns:
            List[Tuple]: [(<YYYY/MM>, <COUNT>)]
        '''
        try:
            query = (("SELECT CONCAT(YEAR(St.StudyDate), '/', "
                      "MONTH(St.StudyDate)) AS StudyMonth, "
                      "COUNT(I.SOPInstanceUID) "
                      f"FROM {modality}_StudyTable St "
                      f"INNER JOIN {modality}_SeriesTable Se "
                      "ON St.StudyInstanceUID = Se.StudyInstanceUID "
                      f"INNER JOIN {modality}_ImageTable I "
                      "ON Se.SeriesInstanceUID = I.SeriesInstanceUID "
                      "GROUP BY StudyMonth;"))

            self.cur.execute(query)
            counts = self.cur.fetchall()

            logging.info(("%s: Successfully counted images per month for "
                          "modality %s."), self.db, modality)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting images per month for modality "
                               "%s: %s"), self.db, modality, error)
            return []

    def count_aggregate_images_per_month(self, modality: str) -> List[Tuple]:
        '''Returns the number of images per month by modality.

        Args:
            modality (str): Modality name.

        Raises:
            error: Mysql error on SELECT.

        Returns:
            List[Tuple]: [(<YYYY/MM>, <COUNT>)]
        '''
        try:
            query = (("SELECT CONCAT(YEAR(St.StudyDate), '/', "
                      "MONTH(St.StudyDate)) AS StudyMonth, "
                      "SUM(I.ORIGINAL + I.DERIVED) AS ImageCount "
                      f"FROM {modality}_StudyTable St "
                      f"INNER JOIN {modality}_SeriesTable Se "
                      "ON St.StudyInstanceUID = Se.StudyInstanceUID "
                      f"INNER JOIN {modality}_Aggregate_ImageType I "
                      "ON Se.SeriesInstanceUID = I.SeriesInstanceUID "
                      "GROUP BY StudyMonth;"))

            self.cur.execute(query)
            counts = self.cur.fetchall()

            logging.info(("%s: Successfully counted images per month for "
                          "modality %s."), self.db, modality)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting images per month for "
                               "modality %s: %s"), self.db, modality, error)
            return []

    def count_sr_per_month(self, column: str) -> List[Tuple]:
        '''Returns counts of given column per month.

        Args:
            column (str): Column on which the count to be performed.

        Raises:
            error: Mysql error on SELECT.

        Returns:
            List[Tuple]: [(<YYYY/MM>, <COUNT>)]
        '''
        try:
            query = (("SELECT CONCAT(YEAR(StudyDate), '/', MONTH(StudyDate)) "
                      f"AS StudyMonth, COUNT(DISTINCT {column}) "
                      "FROM SR_ImageTable "
                      "GROUP BY StudyMonth;"))

            self.cur.execute(query)
            counts = self.cur.fetchall()

            logging.info(("%s: Successfully counted series per month for "
                          "modality SR."), self.db)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: Failed counting series per month for "
                               "modality SR: %s"), self.db, error)
            raise error

    def count_image_nulls(self, modality: str, field: str) -> int:
        '''Counts the number of images where image-level field is NULL.

        Args:
            modality (str): Modality name.
            field (str): Field name.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of images with NULL field.
        '''
        try:
            table = f"{modality}_ImageTable"
            self.cur.execute(f"SELECT COUNT(*) FROM {table} "
                             f"WHERE `{field}` IS NULL;")
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: Table %s has %s rows with NULL for %s.", self.db,
                         table, counts, field)
            return counts
        except mysql.Error as error:
            logging.exception("%s: Failed counting records for table %s: %s",
                              self.db, table, error)
            raise error

    def count_series_nulls(self, modality: str, field: str,
                           aggregate: bool = False) -> int:
        '''Counts the number of images where series-level field is NULL.

        Args:
            modality (str): Modality name.
            field (str): Field name.
            aggregate (bool): Counting by an aggregate table or not.
                              Default to False.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of images with NULL field.
        '''
        try:
            series_table = f"{modality}_SeriesTable"

            if aggregate:
                image_table = f"{modality}_Aggregate_ImageType"
                query = (f"SELECT COUNT(I.ORIGINAL + I.DERIVED) "
                         f"FROM {image_table} AS I "
                         f"INNER JOIN {series_table} AS Se "
                         "ON I.SeriesInstanceUID = Se.SeriesInstanceUID "
                         f"WHERE Se.{field} IS NULL;")
            else:
                image_table = f"{modality}_ImageTable"
                query = (f"SELECT COUNT(*) FROM {image_table} AS I "
                         f"INNER JOIN {series_table} AS Se "
                         "ON I.SeriesInstanceUID = Se.SeriesInstanceUID "
                         f"WHERE Se.{field} IS NULL;")

            self.cur.execute(query)
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: Table %s has %s rows with NULL for %s", self.db,
                         image_table, counts, field)
            return counts
        except mysql.Error as error:
            logging.exception("%s: Failed counting null %s for table %s: %s",
                              self.db, field, image_table, error)
            raise error

    def count_study_nulls(self, modality: str, field: str,
                          aggregate: bool = False) -> int:
        '''Counts the number of images where study-level field is NULL.

        Args:
            modality (str): Modality name.
            field (str): Field name.
            aggregate (bool): Counting by an aggregate table or not.
                              Default to False.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of images with NULL field.
        '''
        try:
            study_table = f"{modality}_StudyTable"
            series_table = f"{modality}_SeriesTable"

            if aggregate:
                image_table = f"{modality}_Aggregate_ImageType"

                query = (f"SELECT COUNT(I.ORIGINAL + I.DERIVED) "
                         f"FROM {image_table} AS I "
                         f"INNER JOIN {series_table} AS Se "
                         "ON I.SeriesInstanceUID = Se.SeriesInstanceUID "
                         f"INNER JOIN {study_table} AS St "
                         "ON Se.StudyInstanceUID = St.StudyInstanceUID "
                         f"WHERE St.{field} IS NULL;")
            else:
                image_table = f"{modality}_ImageTable"
                query = (f"SELECT COUNT(*) FROM {image_table} AS I "
                         f"INNER JOIN {series_table} AS Se "
                         "ON I.SeriesInstanceUID = Se.SeriesInstanceUID "
                         f"INNER JOIN {study_table} AS St "
                         "ON Se.StudyInstanceUID = St.StudyInstanceUID "
                         f"WHERE St.{field} IS NULL;")

            self.cur.execute(query)
            response = self.cur.fetchall()
            counts = response[0][0]

            logging.info("%s: %s images are NULL for field %s in modality %s",
                         self.db, counts, field, modality)
            return counts
        except mysql.Error as error:
            logging.exception(("%s: failed counting images for field %s in "
                               "modality %s: %s"), self.db, field, error,
                              modality)
            raise error

    def group_by_col(self, table: str, column: str) -> List:
        '''Groups a table by given column and returns a list of values and
           counts.

        Args:
            table (str): Table name.
            column (str): Column name.

        Raises:
            error: Mysql error on SELECT COUNT(*).

        Returns:
            int: Number of rows in table.
        '''
        if "Study" in table:
            mod = table.split("_")[0]
            query = (f"SELECT {column}, Count(Se.SeriesDescription) "
                     f"AS Count FROM {table} St INNER JOIN {mod}_SeriesTable "
                     "Se ON St.StudyInstanceUID = Se.StudyInstanceUID GROUP BY "
                     f"{column};")
            logging.debug(f"QUERY: {query}")
        else:
            query = (f"SELECT {column}, COUNT(*) AS Count FROM {table} "
                     f"GROUP BY {column};")

        try:
            self.cur.execute(query)
            response = self.cur.fetchall()

            logging.debug("%s: Grouped %s on table %s.", self.db, column, table)
            return response
        except mysql.Error as error:
            logging.exception("%s: Failed grouping records for table %s: %s",
                              self.db, table, error)

            raise error

    def disconnect(self):
        '''Disconnect from the database.
        '''
        if self.conn is not None:
            self.conn.close()
            logging.info("Successful disconnection from %s", self.db)

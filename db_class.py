import pymongo
import datetime
from pymongo import MongoClient
import pandas as pd
from matplotlib.figure import Figure
import os


# 1 collection: month, year, total expense
# 2 month collection: expense, day, description, time of insertion
PORT = 27017
color_list = ['blue', 'red', 'green', 'yellow', 'black', 'gray', 'gold', 'orange', 'pink', 'magenta', 'cyan', 'salmon',
              'plum', 'lavender']


def split_coll(coll):
    # split the name of the collection
    # es Jun2020 -> ["Jun", "2020"]
    coll = [coll[i:i + 3] for i in range(0, len(coll), 3)]
    coll[1] = coll[1] + coll[2]
    coll.remove(coll[2])
    return coll


def sort_dates(date_list):
    """sorts the list in date order.
        dates in date_list must be in format %b%Y"""
    sort_list = []
    for post in date_list:
        try:
            datetime.datetime.strptime(post, "%b%Y")
        except ValueError:
            continue
        sort_list.append(post)
    days = sorted(sort_list, key=lambda day: datetime.datetime.strptime(day, "%b%Y"))
    return days


class MyDB:
    def __init__(self):
        self.client = MongoClient(host=["mongo:" + str(PORT)], username=os.environ['expense_username'],
                                  password=os.environ['expense_password'])
        # self.client = MongoClient()
        self.db = self.client["expense_tracker"]
        self.global_collection = self.db.Global_Statistics

    def insert(self, coll, query):
        """insert query"""
        self.db[coll].insert_one(query)
        find_coll = split_coll(coll)

        find_query = {"month": find_coll[0],
                      "year": find_coll[1]}

        # if document is already created
        if self.global_collection.find_one(find_query):
            total_expense = self.global_collection.find_one(find_query)["total expense"]
            total_expense += query["expense"]
            self.global_collection.update_one(find_query, {"$set": {"total expense": total_expense}})
        else:
            global_post = {"month": find_coll[0],
                           "year": find_coll[1],
                           "total expense": query["expense"]}
            self.global_collection.insert_one(global_post)

    def delete_coll(self, name):
        """drops a collection deleting the document from global statistics"""
        if name in self.db.list_collection_names():
            coll = self.db[name]
            coll.drop()
            global_del = split_coll(name)
            del_query = {"month": global_del[0],
                         "year": global_del[1]}
            self.delete_doc("Global_Statistics", del_query, False)
        else:
            raise NameError("Name was incorrect")

    def delete_doc(self, coll, query, delete_all=False):
        """delete query"""
        if coll == "Global_Statistics":
            if delete_all:
                self.global_collection.delete_many(query)
            else:
                self.global_collection.delete_one(query)
        elif coll in self.db.list_collection_names():
            selection = self.db[coll]
            if delete_all:
                # update global statistics
                for i in range(0, selection.count_documents(query)):
                    self.global_update(coll, -query["expense"])
                selection.delete_many(query)
            else:
                # update global statistics
                self.global_update(coll, -query["expense"])
                selection.delete_one(query)
            if selection.count_documents({}) == 0:
                selection.drop()
        else:
            raise NameError("Name was incorrect")

    def global_update(self, coll, expense):
        """updates the global collection"""
        coll = split_coll(coll)
        find_query = {"month": coll[0],
                      "year": coll[1]}
        total_expense = self.global_collection.find_one(find_query)["total expense"]
        total_expense += expense
        self.global_collection.update_one(find_query, {"$set": {"total expense": total_expense}})
        if self.global_collection.find_one(find_query)["total expense"] == 0:
            self.delete_doc("Global_Statistics", find_query)

    def update_doc(self, coll, query, new_query, update_all=False):
        """update query"""
        selection = self.db[coll]
        if update_all:
            for i in range(0, selection.count_documents(query)):
                self.global_update(coll, -query["expense"])
                self.global_update(coll, new_query["expense"])
            selection.update_many(query, {"$set": new_query})
        else:
            self.global_update(coll, -query["expense"])
            self.global_update(coll, new_query["expense"])
            selection.update_one(query, {"$set": new_query})

    def find_doc(self, coll, query=None, find_all=False):
        """find query"""
        selection = self.db[coll]
        result_list = []
        if find_all:
            for post in selection.find(query):
                result_list.append(post)
            return result_list
        else:
            return selection.find_one(query)

    def create_dataframe(self, coll, query=None, find_all=True):
        """creates dataframe on a collection"""
        frame = self.find_doc(coll, query, find_all)
        return pd.DataFrame(frame)

    def sort_dataframe(self, df, col):
        """sorts dataframe df on the column col"""
        return df.sort_values(col)

    def plot_dataframe(self, coll, parameters, sort_col='day', mode='solid'):
        """
        Shows the plot of a collection.
        parameters is a tuple of (x_axis, y_axis)
        :param coll: list of collection names (str)
        :param parameters: columns of the collection
        :param sort_col: column to sort on before plotting
        :param mode: equals to linestyle in pd.plot (default 'solid')
        :return: Figure
        """
        # with single input
        fig = Figure()
        if type(coll) == str:
            df = self.create_dataframe(coll)
            if sort_col:
                df = self.sort_dataframe(df, sort_col)
            axis = fig.subplots()
            try:
                xs = [x for x in df[parameters[0]] + df[parameters[2]]]
            except IndexError:
                xs = [x for x in df[parameters[0]]]
            ys = [x for x in df[parameters[1]]]
            axis.plot(xs, ys, linestyle=mode)
        # with multiple input
        else:
            df = []
            for collection in coll:
                df.append(self.create_dataframe(collection))
            coll_title = coll[0]
            # x_ax = None
            axis = fig.subplots()
            for i in range(0, len(coll)):
                if sort_col:
                    df[i] = self.sort_dataframe(df[i], sort_col)
                xs = [x for x in df[i][parameters[0]]]
                ys = [y for y in df[i][parameters[1]]]
                axis.plot(xs, ys, linestyle=mode)
                axis.legend(coll, loc=1)
                try:
                    coll_title = coll_title + " + " + coll[i + 1]
                except IndexError:
                    pass
                axis.set_title(coll_title)
        return fig

    def sort_coll(self, coll, column, ascending=True):
        """sort a collection, ascending order by default"""
        if ascending:
            return self.db[coll].find().sort([(column, pymongo.ASCENDING)])
        else:
            return self.db[coll].find().sort([(column, pymongo.DESCENDING)])

    def sort_global_stats(self):
        """sorts the Global_Statistics collection by date, from the most recent to the oldest"""
        # f1 = lambda k: k['month'] + k['year']
        def f1(k):
            return k['month'] + k['year']

        # f2 = lambda x: datetime.datetime.strptime(f1(x), "%b%Y")
        def f2(x):
            return datetime.datetime.strptime(f1(x), "%b%Y")

        months = sorted(self.find_doc("Global_Statistics", find_all=True), key=lambda a: f2(a))
        self.db["Global_Statistics"].drop()
        self.db["Global_Statistics"].insert_many(months)

    def count_docs(self, coll):
        return self.db[coll].find().count()

    def __str__(self):
        """return the collection list when printing the object"""
        a = self.db.list_collection_names()
        return "%s" % a

    def __bool__(self):
        """return true if it contains at least 1 collection"""
        return len(self.db.list_collection_names()) > 0

    def __len__(self):
        """return how many collections"""
        return len(self.db.list_collection_names())

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        """iterate through collection names"""
        if self.n < len(self.db.list_collection_names()):
            result = self.db.list_collection_names()[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    def __getitem__(self, item):
        """returns the documents in the collection 'item'"""
        if item not in self.db.list_collection_names():
            self.__missing__(item)
        return self.find_doc(item, find_all=True)

    def __missing__(self, key):
        """raises Exception if the database does not have the collection 'key'"""
        if key not in self.db.list_collection_names():
            raise KeyError("Database does not have this collection")

    def __contains__(self, item):
        """returns True if the collection 'item' is inside the database"""
        for post in self.db.list_collection_names():
            if item in post:
                return True

    # rich comparison methods
    def __lt__(self, other):
        return len(self.db.list_collection_names()) < len(other)

    def __le__(self, other):
        return len(self.db.list_collection_names()) <= len(other)

    def __eq__(self, other):
        return len(self.db.list_collection_names()) == len(other)

    def __ne__(self, other):
        return len(self.db.list_collection_names()) != len(other)

    def __gt__(self, other):
        return len(self.db.list_collection_names()) > len(other)

    def __ge__(self, other):
        return len(self.db.list_collection_names()) >= len(other)

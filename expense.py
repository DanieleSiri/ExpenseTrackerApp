from flask import Flask, render_template, escape, request
import db_class
import base64
from io import BytesIO
import os
from _datetime import datetime
app = Flask('ExpenseTracker')


user = os.environ['expense_username']
db = db_class.MyDB()
try:
    sorted_db = db_class.sort_dates(db)
    db.sort_global_stats()
except TypeError:
    pass


def valid_date(day, month, year):
    """checks if the date inserted is valid"""
    try:
        inserted_date = day + "/" + month + "/" + year
        correct_date = datetime.strptime(inserted_date, "%d/%B/%Y")
        # future date or too past back
        if correct_date >= datetime.now() or int(year) < 1900:
            return False
    except ValueError:
        return False
    return True


@app.route('/', methods=['GET', 'POST'])
def index():
    """home page"""
    month = datetime.now().strftime("%b")
    year = datetime.now().strftime("%Y")
    coll = month + year
    try:
        current_expense = db[coll]['expense']
    except KeyError:
        current_expense = 0
    # search query on collections
    if request.method == "POST" and "collection" in request.form and len(db) != 0:
        details = request.form
        try:
            coll_month = details['month']
            coll_year = details['year']
        except KeyError:
            return render_template('index.html', username=user, expense=current_expense, coll_list=db)
        try:
            coll_month = datetime.strptime(coll_month, "%B")
            coll_month = coll_month.strftime("%b")
        except ValueError:
            return render_template('index.html', username=user, expense=current_expense, coll_list=db)
        search_coll = coll_month + coll_year if (coll_month and coll_year) else None
        if search_coll and search_coll not in db:
            search_coll = None
        try:
            only_global = details['global']
        except KeyError:
            only_global = False
        query = {'month': coll_month, 'year': coll_year}
        return render_template('index.html', username=user, expense=current_expense, coll_list=db, coll_s=search_coll,
                               global_s=only_global, query=query)
    # search query on documents
    elif request.method == "POST" and "document" in request.form and len(db) != 0:
        details = request.form
        try:
            coll_month = details['month_d']
            coll_year = details['year_d']
        except KeyError:
            coll_month = None
            coll_year = None
        try:
            coll_month = datetime.strptime(coll_month, "%B")
            coll_month = coll_month.strftime("%b")
        except ValueError:
            pass
        try:
            expense = int(details['expense_d'])
        except (KeyError, ValueError):
            expense = None
        try:
            day = int(details['day_d'])
        except (KeyError, ValueError):
            day = None
        try:
            description = details['description_d']
            if description == '':
                description = None
        except KeyError:
            description = None
        search_coll = coll_month + coll_year if (coll_month and coll_year) else None
        if search_coll and search_coll not in db:
            search_coll = None
        glob_query = {'month': coll_month, 'year': coll_year}
        doc_query = {}
        if expense:
            doc_query['expense'] = int(expense)
        if day:
            doc_query['day'] = int(day)
        if description:
            doc_query['description'] = description
        # if query on a single collection
        if search_coll and db.find_doc(search_coll, doc_query, find_all=True):
            find_q = []
            for doc in db.find_doc(search_coll, doc_query, find_all=True):
                find_q.append(doc)
            find_g = db.find_doc('Global_Statistics', glob_query)
            return render_template('index.html', username=user, expense=current_expense, coll_list=db,
                                   coll_q=search_coll, glob_q=find_g, doc_q=find_q, doc_search=True, single_value=True)
        # if query on single collection fails
        elif search_coll and not db.find_doc(search_coll, doc_query, find_all=True):
            return render_template('index.html', username=user, expense=current_expense, coll_list=db)
        # if query fields are blank
        elif search_coll is None and doc_query == {}:
            return render_template('index.html', username=user, expense=current_expense, coll_list=db)
        else:
            find_g = []
            find_dict = {}
            coll_q = []
            for coll in db:
                if coll == "Global_Statistics":
                    continue
                if db.find_doc(coll, doc_query):
                    find_dict[coll] = []
                    for doc in db.find_doc(coll, doc_query, find_all=True):
                        find_dict[coll].append(doc)
                    if db.find_doc("Global_Statistics", {'month': coll[0:3], 'year': coll[3:]}):
                        find_g.append(db.find_doc("Global_Statistics", {'month': coll[0:3], 'year': coll[3:]}))
                    coll_q.append(coll)
            # if no results were found
            if len(coll_q) == 0:
                return render_template('index.html', username=user, expense=current_expense, coll_list=db)
            return render_template('index.html', username=user, expense=current_expense, coll_list=db,
                                   coll_q=coll_q, glob_q=find_g, doc_q=find_dict, doc_search=True, single_value=False)
    return render_template('index.html', username=user, expense=current_expense, coll_list=db)


@app.route('/<username>/global-statistics')
def print_global(username):
    """global statistics page"""
    # check empty database
    if len(db) != 0:
        try:
            db.sort_global_stats()
        except TypeError:
            pass
        # plot graphic
        data = db.plot_dataframe("Global_Statistics", ['month', 'total expense', 'year'], sort_col=None, mode='dashed')
        buf = BytesIO()
        # Save it to a temporary buffer.
        data.savefig(buf, format="png")
        image = base64.b64encode(buf.getbuffer()).decode("ascii")
        number = db.count_docs("Global_Statistics")
        return render_template('global_statistics.html', documents=db['Global_Statistics'], data=image, doc_num=number+1)
    else:
        return render_template('empty-db.html', username=user)


@app.route('/<username>/database')
def print_db(username):
    """database page"""
    # check empty database
    if len(db) != 0:
        global sorted_db
        sorted_db = db_class.sort_dates(db)
        db.sort_global_stats()
        coll_list = []
        for coll in sorted_db:
            if coll != "Global_Statistics":
                coll_list.append(coll)
        coll_plot = []
        if len(coll_list) == 1:
            coll_plot.append(coll_list[0])
        else:
            for i in range(1, len(coll_list)+1):
                if i == 4:
                    break
                try:
                    coll_plot.append(coll_list[-i])
                except IndexError:
                    break
        data = db.plot_dataframe(coll_plot, ['day', 'expense'])
        buf = BytesIO()
        data.savefig(buf, format="png")
        image = base64.b64encode(buf.getbuffer()).decode("ascii")
        return render_template('db.html', database=db, sorted_database=sorted_db, data=image, db_length=len(db))
    else:
        return render_template('empty-db.html', username=user)


@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'User %s' % escape(username)


@app.route('/<username>/modify', methods=['GET', 'POST'])
def modify(username):
    """insert page"""
    if request.method == "POST":
        global sorted_db
        details = request.form
        try:
            month = details['month']
            year = details['year']
            expense = details['expense']
            day = details['day']
            description = details['description']
        except KeyError:
            return render_template('modify.html', submitted=False)
        try:
            insert = details['insert']
        except KeyError:
            insert = False
        try:
            month_caps = datetime.strptime(month, "%B")
            month = month_caps.strftime("%b")
        except ValueError:
            return render_template('modify.html', submitted=False)
        if not valid_date(day, month_caps.strftime("%B"), year):
            return render_template('modify.html', submitted=False)
        coll = month + year
        query = {'expense': int(expense), 'day': int(day), 'description': description,
                 'time of insertion': datetime.now().strftime("%d/%m/%Y")}
        if insert:
            db.insert(coll, query)
            sorted_db = db_class.sort_dates(db)
            db.sort_global_stats()
            return render_template('modify.html', coll=coll, inserted=query, insert=True, submitted=True)
        else:
            if db.find_doc(coll, query):
                db.delete_doc(coll, query)
                sorted_db = db_class.sort_dates(db)
                db.sort_global_stats()
                return render_template('modify.html', coll=coll, inserted=query, insert=False, submitted=True,
                                       valid=True)
            else:
                return render_template('modify.html', coll=coll, inserted=query, insert=False, submitted=True,
                                       valid=False)
    return render_template('modify.html', submitted=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

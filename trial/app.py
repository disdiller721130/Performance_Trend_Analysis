import os
import pandas as pd
import numpy as np
import pymongo
import statistics

from flask import Flask, request, redirect, url_for, jsonify, render_template
from flask_pymongo import PyMongo

app = Flask(__name__)

conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)
db = client.yield_analysisDB
collection = db.summary_table
app.config["MONGO_URI"] = os.environ.get('MONGODB_URI', '') or "mongodb://localhost:27017/yield_analysisDB"
#mongo = PyMongo(app, uri="mongodb://localhost:27017/yield_analysisDB")
mongo = PyMongo(app)

def bincounter(column):
    bin_column = 0
    for name in column:
        if name != 'App (%)':
            bin_column += 1
        else:
            break
    return bin_column

def signreplace(data):
    OV_FT_Yield_col = data.columns
    for i in range(9, len(OV_FT_Yield_col)):
        if "%" not in OV_FT_Yield_col[i]:                
            del data[OV_FT_Yield_col[i]]
    data = data.replace({"%":""}, regex = True)
    return data

@app.route("/")
def form():
    return render_template("form.html")

@app.route("/send", methods=["GET","POST"])
def send():
    if request.method == "POST":
        file = request.files['file']
        OV_FT_Yield = pd.read_csv(file)
        #OV_FT_Yield_col = OV_FT_Yield.columns
        #for i in range(9, len(OV_FT_Yield_col)):
        #    if "%" not in OV_FT_Yield_col[i]:                
        #        del OV_FT_Yield[OV_FT_Yield_col[i]]
        #OV_FT_Yield = OV_FT_Yield.replace({"%":""}, regex = True)
        OV_FT_Yield = signreplace(OV_FT_Yield)
        #Skip unused data:
        columns_update = OV_FT_Yield.columns  
        bin_column = bincounter(columns_update)

        #FT Yield:
        OV_FT_Yield['Final Yield(%)'] = pd.to_numeric(OV_FT_Yield['Final Yield(%)'])
        final_list = ['week','Lot #','Tot Qty','Final Yield(%)']

        #The other Bins:
        for c in range(bin_column, len(columns_update)):
            OV_FT_Yield[columns_update[c]] = pd.to_numeric(OV_FT_Yield[columns_update[c]])
            final_list.append(columns_update[c])

        OV_FT_Yield_aft = OV_FT_Yield[final_list]
        OV_summary_list = OV_FT_Yield_aft.to_dict('list')
        mongo.db.summary_table.insert_one(OV_summary_list)
        return redirect("/", code=302)

@app.route("/week_list")
def week_list():
    summary_transfer = mongo.db.summary_table.find_one()
    yield_summary_db = pd.DataFrame(summary_transfer)
    del yield_summary_db["_id"]
    week = yield_summary_db.groupby(["week"]).mean()
    return jsonify(list(week.index.values))

@app.route("/overall_items")
def overall_items():
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    item_list = list(transfer_data.columns[3:])
    return jsonify(item_list)

@app.route("/overall_trend/<result>")
def overall_trend(result):
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    yield_dict = {}
    transfer_data['sum'] = transfer_data['Tot Qty'] * transfer_data[result]
    transfer_data_gp = transfer_data.groupby(['week']).sum()
    #Fixed 9-week period:
    week_len = len(transfer_data_gp.index.values.tolist())
    if week_len > 9:
        transfer_data_gp = transfer_data_gp[(week_len - 9):]

    yield_dict[result] = transfer_data_gp['sum'].tolist()
    yield_dict['total_die'] = transfer_data_gp['Tot Qty'].tolist()
    yield_dict['week'] = transfer_data_gp.index.values.tolist()
    FT_Yield = pd.DataFrame(yield_dict)
    yield_dict[result] = list(FT_Yield[result] / FT_Yield['total_die'])
    return jsonify(yield_dict)

@app.route("/overall_box/<result>")
def overall_box(result):
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    overall_dict = {}
    week_list = list(transfer_data.groupby(['week']).count().index.values)
    #Fixed 9-week period:
    week_len = len(week_list)
    if week_len > 9:
        update_weeklist = week_list[(week_len) - 9]
    else:
        update_weeklist = week_list

    for week in update_weeklist:
        bin_weeklock = transfer_data.set_index('week')
        bin_details = bin_weeklock.loc[week,result].tolist()
        overall_dict[week] = bin_details

    return jsonify(overall_dict)

@app.route("/FT_pie/<week>")
def FT_pie(week):
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    data_column = transfer_data.columns
    total_die = transfer_data['Tot Qty'].sum()
    item_fr_dict = {}

    #FT Yield:
    transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data['Final Yield(%)']
    item_fr_dict['Final Yield(%)'] = transfer_data['sumproduct'].sum() / total_die

    #The other Bins:
    for c in range(4, len(data_column)):
        transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data[data_column[c]]
        item_fr_dict[data_column[c]] = transfer_data['sumproduct'].sum() / total_die
    del transfer_data['sumproduct']

    #Total top10:
    item_fr_df = pd.DataFrame(item_fr_dict, index=[0])
    item_fr_df = item_fr_df.T
    item_fr_df = item_fr_df.rename(columns = {0:'Performance'})
    item_fr_df = item_fr_df.reset_index(drop = False).rename(columns = {'index': 'FT_Item'})
    FT_list_all = item_fr_df['FT_Item'].tolist()

    #FT top10:
    index_stop = 0
    for item in FT_list_all:
        if item != '96OTHERS1(%)':
            index_stop += 1
        else:
            break
    FT_summary_df = item_fr_df[0:index_stop].sort_values('Performance', ascending = False)
    FT_list = list(FT_summary_df['FT_Item'][:7])
    FT_list.remove("App (%)")

    #Yield/loss by week:
    total_items = FT_list
    yield_dict = {}
    for item in total_items:
        transfer_data['sum'] = transfer_data['Tot Qty'] * transfer_data[item]
        transfer_data_gp = transfer_data.groupby(['week']).sum()
        yield_dict[item] = transfer_data_gp['sum'].tolist()
        yield_dict['total_die'] = transfer_data_gp['Tot Qty'].tolist()
        yield_dict['week'] = transfer_data_gp.index.values.tolist()
        FT_Yield = pd.DataFrame(yield_dict)
        FT_Yield[item] = FT_Yield[item] / FT_Yield['total_die']
        yield_dict[item] = FT_Yield[item].tolist()
    yield_WeeklyAvg = pd.DataFrame(yield_dict).set_index('week')

    #loss by week:
    loss_WeeklyAvg = yield_WeeklyAvg.T[2:]

    loss_dict = {}
    item_list = []
    fail_list = []
    loss_Weekly = loss_WeeklyAvg.to_dict()
    for key,value in loss_Weekly[week].items():
        item_list.append(key)
        fail_list.append(value)
    loss_dict['item'] = item_list
    loss_dict['fail'] = fail_list
    return jsonify(loss_dict)

@app.route("/SLT_pie/<week>")
def SLT_pie(week):
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    data_column = transfer_data.columns
    total_die = transfer_data['Tot Qty'].sum()
    item_fr_dict = {}

    #FT Yield:
    transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data['Final Yield(%)']
    item_fr_dict['Final Yield(%)'] = transfer_data['sumproduct'].sum() / total_die

    #The other Bins:
    for c in range(4, len(data_column)):
        transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data[data_column[c]]
        item_fr_dict[data_column[c]] = transfer_data['sumproduct'].sum() / total_die
    del transfer_data['sumproduct']

    #Total top10:
    item_fr_df = pd.DataFrame(item_fr_dict, index=[0])
    item_fr_df = item_fr_df.T
    item_fr_df = item_fr_df.rename(columns = {0:'Performance'})
    item_fr_df = item_fr_df.reset_index(drop = False).rename(columns = {'index': 'FT_Item'})
    FT_list_all = item_fr_df['FT_Item'].tolist()

    #SLT top10:
    index_start= 0
    for item in FT_list_all:
        if item != '101SpecialPASS1(%)':
            index_start += 1
        else:
            break
    SLT_summary_df = item_fr_df[index_start:].sort_values('Performance', ascending = False)
    SLT_summary_df = SLT_summary_df.rename(columns = {'FT_Item':'SLT_Item'})
    SLT_list = list(SLT_summary_df['SLT_Item'][:5])

    #Yield/loss by week:
    total_items = SLT_list
    yield_dict = {}
    for item in total_items:
        transfer_data['sum'] = transfer_data['Tot Qty'] * transfer_data[item]
        transfer_data_gp = transfer_data.groupby(['week']).sum()
        yield_dict[item] = transfer_data_gp['sum'].tolist()
        yield_dict['total_die'] = transfer_data_gp['Tot Qty'].tolist()
        yield_dict['week'] = transfer_data_gp.index.values.tolist()
        FT_Yield = pd.DataFrame(yield_dict)
        FT_Yield[item] = FT_Yield[item] / FT_Yield['total_die']
        yield_dict[item] = FT_Yield[item].tolist()
    yield_WeeklyAvg = pd.DataFrame(yield_dict).set_index('week')
    del yield_WeeklyAvg['total_die']

    #loss by week:
    loss_WeeklyAvg = yield_WeeklyAvg.T

    loss_dict = {}
    item_list = []
    fail_list = []
    loss_Weekly = loss_WeeklyAvg.to_dict()
    for key,value in loss_Weekly[week].items():
        item_list.append(key)
        fail_list.append(value)
    loss_dict['item'] = item_list
    loss_dict['fail'] = fail_list
    return jsonify(loss_dict)

@app.route("/top10_list")
def top10_list():
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    data_column = transfer_data.columns
    total_die = transfer_data['Tot Qty'].sum()
    item_fr_dict = {}

    #FT Yield:
    transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data['Final Yield(%)']
    item_fr_dict['Final Yield(%)'] = transfer_data['sumproduct'].sum() / total_die

    #The other Bins:
    for c in range(4, len(data_column)):
        transfer_data['sumproduct'] = transfer_data['Tot Qty'] * transfer_data[data_column[c]]
        item_fr_dict[data_column[c]] = transfer_data['sumproduct'].sum() / total_die
    del transfer_data['sumproduct']

    #FT top10:
    item_fr_df = pd.DataFrame(item_fr_dict, index=[0])
    item_fr_df = item_fr_df.T
    item_fr_df = item_fr_df.rename(columns = {0:'Performance'})
    item_fr_df = item_fr_df.reset_index(drop = False).rename(columns = {'index': 'FT_Item'})
    FT_list_all = item_fr_df['FT_Item'].tolist()
    index_stop = 0
    for item in FT_list_all:
        if item != '96OTHERS1(%)':
            index_stop += 1
        else:
            break
    FT_summary_df = item_fr_df[0:index_stop].sort_values('Performance', ascending = False)
    FT_list = list(FT_summary_df['FT_Item'][:7])

    #SLT top10:
    index_start= 0
    for item in FT_list_all:
        if item != '101SpecialPASS1(%)':
            index_start += 1
        else:
            break
    SLT_summary_df = item_fr_df[index_start:].sort_values('Performance', ascending = False)
    SLT_summary_df = SLT_summary_df.rename(columns = {'FT_Item':'SLT_Item'})
    SLT_list = list(SLT_summary_df['SLT_Item'][:5])
    total_list = FT_list + SLT_list
    return jsonify(total_list)

@app.route("/SLLY_list/<hbin>")
def SLLY_list(hbin):
    summary_transfer = mongo.db.summary_table.find_one()
    transfer_data = pd.DataFrame(summary_transfer)
    del transfer_data["_id"]
    
    #FT Spec:
    FT_spec_summary = {}
    if hbin == 'Final Yield(%)':
        FT_spec_summary[hbin] = statistics.median(transfer_data[hbin])\
        - (4 * statistics.stdev(transfer_data[hbin]))
    else:
        FT_spec_summary[hbin] = statistics.median(transfer_data[hbin])\
        + (4 * statistics.stdev(transfer_data[hbin]))

    #FT weekly bad lots:
    FT_lot_summary = {}
    if hbin == 'Final Yield(%)':
        FT_specific = transfer_data.loc[:,['Lot #',hbin]]
        FT_specific = FT_specific.loc[FT_specific[hbin] < FT_spec_summary[hbin],:]
        FT_lot_summary[hbin] = list(FT_specific['Lot #'])
        if len(FT_lot_summary[hbin]) == 0:
            FT_lot_summary[hbin] = "No LY lots over the past 9 weeks."
    else:
        FT_specific = transfer_data.loc[:,['Lot #',hbin]]
        FT_specific = FT_specific.loc[FT_specific[hbin] > FT_spec_summary[hbin],:]
        FT_lot_summary[hbin] = list(FT_specific['Lot #'])
        if len(FT_lot_summary[hbin]) == 0:
            FT_lot_summary[hbin] = "No LY lots over the past 9 weeks."
            
    print(FT_lot_summary)
    return jsonify(FT_lot_summary)

#Drop the collection in the end:
db.summary_table.delete_one({})

if __name__ == "__main__":
    app.run()
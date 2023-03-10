from asyncio.windows_events import NULL
import io
from pickle import FALSE
from django.shortcuts import render
from .models import Vehicle, Passes, Station, Provider
#from django.forms import MemberForm
from .resources import StationResource
from django.contrib import messages
from tablib import Dataset, Databook
from django.http import HttpResponse, JsonResponse, HttpRequest
from rest_framework.parsers import JSONParser
from .serializers import *
from rest_framework.response import Response
from rest_framework import generics, status
from django.http import Http404
from rest_framework.views import APIView
from datetime import datetime
from django.db.models import Sum
from django.db import connection
from django.db.utils import OperationalError
import csv
import requests
from datetime import datetime
from django.core.exceptions import ValidationError, BadRequest
#import plotly.graph_objects as go
#import plotly as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot
import plotly.express as px
import plotly


def upload_from_xslx(request):
    if request.method == 'POST':
        # station_resource = StationResource()
        dataset = Databook()
        new_station = request.FILES['myfile']

        if not new_station.name.endswith('xlsx'):
            messages.info(request, 'wrong format')
            return render(request, 'upload.html')

        imported_data = dataset.load(new_station.read(), format='xlsx')
        for datasheet in imported_data.sheets():
            print(datasheet.title)
            if datasheet.title == 'providers':
                for data in datasheet:
                    if data[0] == None:
                        break
                    value = Provider()
                    value.providerAbbr = data[0]
                    value.providerName = data[1]
                    value.iban = data[2]
                    value.bankname = data[3]
                    value.save()
            elif datasheet.title == 'stations':
                for data in datasheet:
                    if data[0] == None:
                        break
                    value = Station()
                    value.stationid = data[0]
                    #value.stationProvider = data[1]
                    value.stationName = data[2]
                    value.station_fk = Provider.objects.get(
                        providerName=data[1])
                    value.save()
            elif datasheet.title == 'vehicles_100':

                for data in datasheet:
                    if data[0] == None:
                        break
                    value = Vehicle()
                    value.vehicleid = data[0]
                    value.tagid = data[1]
                    value.licenceYear = data[4]
                    #value.tagProvider = data[2]
                    #value.tagProviderAbbr = data[3]
                    value.vehicle_fk1 = Provider.objects.get(
                        providerName=data[2])
                    value.save()
            elif datasheet.title == 'passes100_8000':
                for data in datasheet:
                    if data[0] == None:
                        break
                    value = Passes()
                    value.passid = data[0]
                    value.timestamp = data[1]
                    value.charge = data[4]
                    #value.stationRef = data[2]
                    #value.vehicleRef = data[3]
                    value.passes_fk1 = Station.objects.get(stationid=data[2])
                    value.passes_fk2 = Vehicle.objects.get(vehicleid=data[3])
                    value.save()

    return render(request, 'upload.html')


def mainpage(request):

    return render(request, 'mainpage.html')


def info(request):
    return render(request, 'info.html')


def passupdt(request):
    if request.method == 'POST':
        dataset = Dataset()
        csv_file = request.FILES['myfile']
        csvreader = csv.reader(io.StringIO(
            csv_file.read().decode('utf-8')), delimiter=';')
        header = next(csvreader)
        # imported_data = dataset.load(io.StringIO(
        #     csv_file.read().decode('utf-8')), 'csv')
        # print(imported_data)
        for data in csvreader:
            try:
                if data[0] == None:
                    break
                value = Passes()
                value.passid = data[0]
                value.timestamp = datetime.strptime(
                    data[1], "%d/%m/%Y %H:%M")
                value.charge = data[4]
                value.passes_fk1 = Station.objects.get(stationid=data[2])
                value.passes_fk2 = Vehicle.objects.get(vehicleid=data[3])
                try:
                    value.full_clean()
                except ValidationError:
                    raise BadRequest("Error 400 - Bad Request")
                value.save()
            except:
                raise BadRequest("Error 400 - Bad Request")
    return render(request, 'passupdt.html')
   

def transauth(request):
    operator = Provider.objects.all()
    plot_div = NULL
    plot_div2 = NULL
    if request.method == 'POST':
        form = request.POST
        dt = form["DateTo"]
        df = form["DateFrom"]
        print(form)
        dt = datetime.strptime(dt, "%Y-%m-%d").strftime("%Y%m%d")
        df = datetime.strptime(df, "%Y-%m-%d").strftime("%Y%m%d")
        # temp1 = datetime.strptime(dt, "%Y%m%d")
        # temp2 = datetime.strptime(df, "%Y%m%d")
        # temp_interval = temp2 - temp1
        # day_interval = temp_interval.days
        plot_type = form["Diagram Type"]
        print(type(dt))
        url = 'http://127.0.0.1:8000/interoperability/api/PassesAnalysis/' + \
            form["op1"] + '/' + form["op2"] + '/' + df + '/' + dt
        passes = requests.get(url, verify=False).json()
        #print(passes)
        if plot_type=="Scatter Diagram":
            data = passes['PassesList']
            #x = temp1 + pd.to_timedelta(np.arange(day_interval), 'D')
            x_index = pd.date_range(df, dt)
            x = x_index.date
            #print(type(x[0]))
            y = []
            for i in x:
                passes_count = 0
                for j in data:
                    tempdate = datetime.strptime(j['timestamp'], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
                    tempstring = i.strftime("%Y-%m-%d")
                    if tempdate==tempstring:
                        passes_count+=1
                y.append(passes_count)
            #print(x)
            #print(y)
            layout1 = go.Layout(
                title = 'Passes per Day Scatter',
                xaxis_title = 'Day',
                yaxis_title = 'Number of Passes',
                height = 420,
                width = 560,
            )
            plot_div = plot({'data': [go.Scatter(x = x, y = y, opacity=0.8, name="plot")], 'layout': layout1}, output_type='div')
        elif plot_type=="Bar Diagram":
            data = passes['PassesList']
            #x = temp1 + pd.to_timedelta(np.arange(day_interval), 'D')
            x_index = pd.date_range(df, dt)
            x = x_index.date
            #print(type(x[0]))
            y = []
            for i in x:
                passes_count = 0
                for j in data:
                    tempdate = datetime.strptime(j['timestamp'], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
                    tempstring = i.strftime("%Y-%m-%d")
                    if tempdate==tempstring:
                        passes_count+=1
                y.append(passes_count)
            #print(x)
            #print(y)
            layout = go.Layout(
                title = 'Passes per Day Bar',
                xaxis_title = 'Day',
                yaxis_title = 'Number of Passes',
                height = 420,
                width = 560,
            )
            plot_div = plot({'data': [go.Bar(x = x, y = y, opacity=0.8, name="plot")], 'layout': layout}, output_type='div')
    return render(request, 'transauth.html', context={'operators': operator, 'plot': plot_div})


def passescost(request):
    operator = Provider.objects.all()
    if request.method == 'POST':
        form = request.POST
        dt = form["DateTo"]
        df = form["DateFrom"]
        print(form)
        dt = datetime.strptime(dt, "%Y-%m-%d").strftime("%Y%m%d")
        df = datetime.strptime(df, "%Y-%m-%d").strftime("%Y%m%d")
        url = 'http://127.0.0.1:8000/interoperability/api/PassesCost/' + \
            form["op1"] + '/' + form["op2"] + '/' + df + '/' + dt
        data = requests.get(url, verify=False).json()
        print(data)
        return render(request, 'passescostres.html', {'res': data.values()})
    return render(request, 'passescost.html', {'operators': operator})


class PassesPerStation(APIView):
    def check(self, pk, df, dt):
        station = Station.objects.filter(stationid=pk)
        if not station.exists():
            raise BadRequest("Invalid arguments: Station does not exist")
        if(df > dt):
            raise BadRequest("Invalid arguments: date_from > date_to")
        return station[0]

    def get_object(self, pk, df, dt):
        passes = Passes.objects.filter(passes_fk1__stationid=pk).exclude(
            timestamp__gte=dt).filter(timestamp__gte=df)
        if(passes.exists()):
            return passes
        return []

    def get(self, request, pk, df, dt):
        try:
            dt = datetime.strptime(dt+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
            df = datetime.strptime(df+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
        except:
            raise BadRequest("Wrong DateTime Format")
        try:
            format = request.GET['format']
        except:
            format = 'json'
        station = self.check(pk, df, dt)
        passes = self.get_object(pk, df, dt)
        serializer = PassesSerializer(passes, many=True)
        header = {}
        header["Station"] = pk
        header["StationOperator"] = station.stationProvider
        header["RequestTimeStamp"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        header["PeriodFrom"] = df
        header["PeriodTo"] = dt
        try:
            header["NumberOfPasses"] = passes.count()
        except:
            header["NumberOfPasses"] = 0
        header["PassesList"] = []
        #augmented_serializer_data = list(serializer.data)
        #augmented_serializer_data.insert(0, header)
        index = 0
        for data in serializer.data:
            index += 1
            Vehicle = passes[index-1].passes_fk2
            Vehicle_tagProvider = Vehicle.tagProvider
            data["PassIndex"] = index
            data["TagProvider"] = Vehicle_tagProvider
            data.pop("stationRef")
            if format == 'json':
                header["PassesList"].append(data)

        if format == 'json':
            return Response(header)
        return Response(serializer.data)


class PassesAnalysis(APIView):
    def check(self, op1_ID, op2_ID, df, dt):
        provider1 = Provider.objects.filter(providerAbbr=op1_ID)
        provider2 = Provider.objects.filter(providerAbbr=op2_ID)
        if (not provider1.exists()) or (not provider2.exists()):
            raise BadRequest("Invalid arguments: Provider does not exist")
        if(df > dt):
            raise BadRequest("Invalid arguments: date_from later than date_to")
        return (provider1[0], provider2[0])

    def get_object(self, op1_ID, op2_ID, df, dt):
        passes = Passes.objects.filter(passes_fk1__station_fk__providerAbbr=op1_ID).filter(
            passes_fk2__vehicle_fk1__providerAbbr=op2_ID).exclude(timestamp__gte=dt).filter(timestamp__gte=df)
        if(passes.exists()):
            return passes
        return []

    def get(self, request, op1_ID, op2_ID, df, dt):
        try:
            dt = datetime.strptime(dt+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
            df = datetime.strptime(df+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
        except:
            raise BadRequest("Wrong DateTime Format")
        try:
            format = request.GET['format']
        except:
            format = 'json'
        self.check(op1_ID, op2_ID, df, dt)
        passes = self.get_object(op1_ID, op2_ID, df, dt)
        serializer = PassesSerializer(passes, many=True)
        augmented_serializer_data = list(serializer.data)

        info = {}
        info["op1_ID"] = op1_ID
        info["op2_ID"] = op2_ID
        info["RequestTimeStamp"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        info["PeriodFrom"] = df
        info["PeriodTo"] = dt
        try:
            info["NumberOfPasses"] = passes.count()
        except:
            info["NumberOfPasses"] = 0
        info["PassesList"] = []
        #augmented_serializer_data.insert(0, info)
        index = 0
        for data in serializer.data:
            index += 1
            data["PassIndex"] = index
            data.pop("pass_type")
            info["PassesList"].append(data)

        if (format == 'json'):
            return Response(info, content_type='json')
        return Response(info["PassesList"])


class PassesCost(APIView):
    def check(self, op1_ID, op2_ID, df, dt):
        provider1 = Provider.objects.filter(providerAbbr=op1_ID)
        provider2 = Provider.objects.filter(providerAbbr=op2_ID)
        if (not provider1.exists()) or (not provider2.exists()):
            raise BadRequest("Invalid arguments: Provider does not exist")
        if(df > dt):
            raise BadRequest("Invalid arguments: date_from > date_to")
        return provider1[0]

    def get_object(self, op1, op2, df, dt):
        passes = Passes.objects.filter(passes_fk1__station_fk__providerAbbr=op1).filter(
            passes_fk2__vehicle_fk1__providerAbbr=op2).exclude(timestamp__gte=dt).filter(timestamp__gte=df)
        if(passes.exists()):
            return passes
        return []

    def get(self, request, op1, op2, df, dt):
        try:
            dt = datetime.strptime(dt+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
            df = datetime.strptime(df+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
        except:
            raise BadRequest("Wrong DateTime Format")
        try:
            format = request.GET['format']
        except:
            format = 'json'
        provider = self.check(op1, op2, df, dt)
        passes = self.get_object(op1, op2, df, dt)
        data = {}
        data["Operator1"] = op1
        data["Operator2"] = op2
        data["RequestTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["PeriodFrom"] = df
        data["PeriodTo"] = dt
        try:
            data["NumberOfPasses"] = passes.count()
            data["PassesCost"] = passes.aggregate(Sum('charge'))["charge__sum"]
        except:
            data["NumberOfPasses"] = 0
            data["PassesCost"] = 0
        return Response(data)


class ChargesBy(APIView):
    def check(self, op1_ID, df, dt):
        provider1 = Provider.objects.filter(providerAbbr=op1_ID)
        if (not provider1.exists()):
            raise BadRequest("Invalid arguments: Provider does not exist")
        if(df > dt):
            raise BadRequest("Invalid arguments: date_from > date_to")
        return provider1[0]

    def get_object(self, op1, op2, df, dt):
        passes = Passes.objects.filter(passes_fk1__station_fk__providerAbbr=op1).filter(
            passes_fk2__vehicle_fk1__providerAbbr=op2).exclude(timestamp__gte=dt).filter(timestamp__gte=df)
        if(passes.exists()):
            return passes
        return []

    def get(self, request, op1, df, dt):
        try:
            dt = datetime.strptime(dt+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
            df = datetime.strptime(df+"000000", "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S")
        except:
            raise BadRequest("Wrong DateTime Format")
        try:
            format = request.GET['format']
        except:
            format = 'json'
        self.check(op1, df, dt)
        response = {"opID": op1, "RequestTimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PeriodFrom": df,
                    "PeriodTo": dt, "PPOList": []}
        for provider in Provider.objects.all():
            op2 = provider.providerAbbr
            if op2 == op1:
                continue
            passes = self.get_object(op1, op2, df, dt)
            try:
                pcount = passes.count()
                psum = passes.aggregate(Sum('charge'))["charge__sum"]
            except:
                pcount = 0
                psum = 0
            dict = {"VisitingOperator": op2,
                    "NumberOfPasses": pcount, "PassesCost": psum}
            response["PPOList"].append(dict)
        if format == 'json':
            return Response(response)
        return Response(response["PPOList"])


class PassesUpdate(APIView):
    def get(self, request, format=None):
        snippets = Passes.objects.all()
        serializer = PassesSerializerAll(snippets, many=True)
        return Response(serializer.data)
        # return(render(request, 'passupdt.html'))

    def post(self, request):
        try:
            format = request.GET['format']
        except:
            format = 'json'
        if format == "json":
            for data in request.data:
                try:
                    value = Passes()
                    value.passid = data["passID"]
                    value.timestamp = data["timestamp"]
                    value.charge = data["charge"]
                    value.passes_fk1 = Station.objects.get(
                        stationid=data["stationRef"])
                    value.passes_fk2 = Vehicle.objects.get(
                        vehicleid=data["vehicleRef"])

                    try:
                        value.full_clean()
                    except ValidationError:
                        raise BadRequest("Error 400 - Bad Request")
                    value.save()
                except:
                    raise BadRequest("Error 400 - Bad Request")
            return Response([{"status": "OK"}])

        if format == "csv":
            dataset = Dataset()
            csv_file = request.FILES['file']
            csvreader = csv.reader(io.StringIO(
                csv_file.read().decode('utf-8')), delimiter=';')
            header = next(csvreader)
            # imported_data = dataset.load(io.StringIO(
            #     csv_file.read().decode('utf-8')), 'csv')
            # print(imported_data)
            for data in csvreader:
                try:
                    if data[0] == None:
                        break
                    value = Passes()
                    value.passid = data[0]
                    value.timestamp = datetime.strptime(
                        data[1], "%d/%m/%Y %H:%M")
                    value.charge = data[4]
                    value.passes_fk1 = Station.objects.get(stationid=data[2])
                    value.passes_fk2 = Vehicle.objects.get(vehicleid=data[3])
                    try:
                        value.full_clean()
                    except ValidationError:
                        raise BadRequest("Error 400 - Bad Request")
                    value.save()
                except:
                    raise BadRequest("Error 400 - Bad Request")
            return Response([{"status": "OK"}])
        return Response([{"status": "Unsupported format method"}])


class healthcheck(APIView):
    def get(self, request):
        try:
            connection.ensure_connection()
            return Response([{"status": "OK", "dbconnection": "Connected"}])
        except OperationalError:
            return Response([{"status": "failed"}])


class resetpasses(APIView):
    def post(self, request):
        try:
            # for instance in Passes.objects.all().iterator():
            #     instance.delete()
            objects_to_del = Passes.objects.all()
            objects_to_del.delete()
            return Response([{"status": "OK"}])
        except BaseException as err:
            print(f"Unexpected {err=}, {type(err)=}")
            return Response([{"status": "failed", "error type": str(err)}])
        except:
            return Response([{"status": "failed"}])


class resetstations(APIView):
    def post(self, request):
        try:
            for instance in Station.objects.all().iterator():
                instance.delete()
            with open("tl2175app/starting_data/sampledata01_stations.csv", "r") as f:
                csvreader = csv.reader(f, delimiter=';')
                header = next(csvreader)
                for row in csvreader:
                    value = Station()
                    value.stationid = row[0]
                    value.stationName = row[2]
                    value.station_fk = Provider.objects.get(
                        providerName=row[1])
                    value.save()
            return Response([{"status": "OK"}])
        except BaseException as err:
            print(f"Unexpected {err=}, {type(err)=}")
            return Response([{"status": "failed", "error type": str(err)}])
        except:
            return Response([{"status": "failed"}])


class resetvehicles(APIView):
    def post(self, request):
        try:
            for instance in Vehicle.objects.all().iterator():
                instance.delete()
            with open("tl2175app/starting_data/sampledata01_vehicles_100.csv", "r") as f:
                csvreader = csv.reader(f, delimiter=';')
                header = next(csvreader)
                for row in csvreader:
                    value = Vehicle()
                    value.vehicleid = row[0]
                    value.tagid = row[1]
                    value.licenceYear = row[4]
                    value.vehicle_fk1 = Provider.objects.get(
                        providerName=row[2])
                    value.save()
            return Response([{"status": "OK"}])
        except BaseException as err:
            print(f"Unexpected {err=}, {type(err)=}")
            return Response([{"status": "failed", "error type": str(err)}])
        except:
            return Response([{"status": "failed"}])


class configurePayments(APIView):
    def check(self, op1, op2, df, dt):
        provider1 = Provider.objects.filter(providerAbbr=op1)
        provider2 = Provider.objects.filter(providerAbbr=op2)
        if (not provider1.exists()) or (not provider2.exists()):
            raise BadRequest("Invalid arguments: Provider does not exist")
        if(df > dt):
            raise BadRequest("Invlide arguments: date_from > date_to")
        return (provider1[0], provider2[0])

    def get(self, request, op1, op2, df, dt):
        try:
            format = request.GET['format']
        except:
            format = 'json'
        self.check(op1, op2, df, dt)

        url = 'http://127.0.0.1:8000/interoperability/api/PassesCost/' + \
            op1 + '/' + op2 + '/' + df + '/' + dt
        print(requests.get(url))
        cost_op1 = (requests.get(url).json())['PassesCost']
        url = 'http://127.0.0.1:8000/interoperability/api/PassesCost/' + \
            op2 + '/' + op1 + '/' + df + '/' + dt
        cost_op2 = (requests.get(url).json())["PassesCost"]

        final_cost = cost_op1 - cost_op2
        res = {}
        res["operators"] = op1 + " " + op2
        res["cost"] = final_cost
        if(format == 'json'):
            return Response(res, content_type='json')
        return Response(res)

from django.shortcuts import render
from .forms import *
from reports.models import *
from django.shortcuts import render_to_response, render
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.postgres.search import SearchVector
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from registration.models import UserProfile
from django.core.files import File
import os
from django.conf import settings
import mimetypes
from django.utils.encoding import smart_str
from Crypto.PublicKey import *
from django.db.models import Q


# Create your views here.
@csrf_exempt
def createReport(request):
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES)
        files = FileForm(request.FILES.getlist('document'))
        if form.is_valid() and files.is_valid():
            checked = False
            encrypted = False
            if request.POST.get("is_private", False):
                checked =True
                encrypted = True
            if request.POST.get("is_encrypted", False):
                encrypted = True
            # clean_title = form.clean('title')
            newdoc = report(title=form.cleaned_data['title'],
                timestamp=timezone.now(),
                short_description=form.cleaned_data['short_description'],
                detailed_description=form.cleaned_data['detailed_description'],
                is_private = checked,
                location=form.cleaned_data['location'],
                is_encrypted = encrypted,
                username_id= request.user)
            newdoc.save()
            file = request.FILES.getlist('document')
            for f in file:
                if newdoc.is_encrypted == True:
                    pubKey = UserProfile.objects.get(user_id=newdoc.username_id_id).publicKey
                    pubKeyOb = bytes(pubKey, 'utf-8')
                    pubKeyOb = RSA.importKey(pubKey)
                    newfile = Document(document=f, report_document=newdoc, name=f)
                    newfile.save()
                    encrypt_file(pubKeyOb, str(f))
                else:
                    newfile = Document(document=f, report_document=newdoc, name=f)
                    newfile.save()


    else:
        form = ReportForm()
        files = FileForm()
    variables = RequestContext(request, {
        'form': form,
        'files': files,
    })


    return render_to_response(
        'reports/createReports.html',
        variables,
    )


def encrypt_file(key, filename):
    file = settings.MEDIA_ROOT + '/documents/' + filename
    print(file)
    print(type(file))
    with open(file, 'rb') as in_file:
        with  open(file + '.enc','wb') as out_file:
            #while True:
            chunk = in_file.read(1000)
            print(chunk)
                #if len(chunk) == 0:
                 #   break
            chunk = bytes(chunk, 'utf-8')
            print(chunk)
            encrypted = key.encrypt(chunk, 32)
            out_file.write(encrypted)

@csrf_exempt
def createFolder(request):
    reports = report.objects.all()
    username_id = request.user
    if request.method == 'POST':
        form = FolderForm(request.POST, request.FILES)
        selected = request.POST.getlist('selected_report[]')
        if form.is_valid():
            folder_object = folder.objects.create(
                title=form.cleaned_data['title'], username_id=username_id
            )
            for report_selected in selected:
                re = report.objects.get(title=report_selected)
                folder_object.added_reports.add(re)

    else:
        form = FolderForm()
    variables = RequestContext(request, {
        'form': form, 'reports':reports
    })

    return render_to_response(
        'reports/createFolder.html',
        variables,
    )
def renameFolder(request):
    folders = folder.objects.all()
    selected = request.POST.getlist('selected_folder[]')
    if request.method == 'POST':
        form = FolderForm(request.POST)
        if form.is_valid():
            title=form.cleaned_data['title']

            for folder_selected in selected:
                print(folder_selected)
                fs = folder.objects.get(title=folder_selected)
                fs.title = title
                fs.save()
    else:
        form = FolderForm()
    variables = RequestContext(request, {
        'form': form, 'folders':folders
    })

    return render_to_response(
        'reports/renameFolder.html',
        variables,
    )

def deleteFolder(request):
    folders = folder.objects.all()
    selected = request.POST.getlist('selected_folder[]')
    if request.method == 'POST':
        for folder_selected in selected:
            fs = folder.objects.get(title=folder_selected)
            fs.delete()
    else:
        pass
    variables = RequestContext(request, {
        'folders': folders
    })

    return render_to_response(
        'reports/deleteFolder.html',
        variables,
    )



def viewFolder(request):
    user = request.user
    folders = folder.objects.all()
    reports = folder.objects.all()
    return render(request, 'reports/viewFolders.html', {'folders': folders, 'reports':reports, 'user': user})

def viewReports(request):
    user = request.user
    reports = report.objects.all().filter(is_private="False")
    folders = folder.objects.all()
    return render(request, 'reports/viewReports.html', {'user': user, 'reports': reports, 'folders':folders})

def viewReport(request):
    user = request.user
    title = request.POST.get("selected_report")
    rs = report.objects.get(title=title)
    files = Document.objects.all().filter(report_document=rs.id)
    owner = User.objects.get(id=rs.username_id_id)

    print(owner.username)
        #title = request.POST.getlist("selected_report[]")
    #for report_selected in title:
     #   rs = report.objects.get(title=report_selected)
    #filename = os.path.realpath(rs.document)
    #filename = "media/" + str(rs.document)
    #f = open(filename, 'r')
    #myFile = File(f)
    #print(filename)
    #wrapper = FileWrapper(File(filename))
    #response = HttpResponse(myFile)
    #response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(filename)
    return render(request, 'reports/viewReportDescription.html', {'rs': rs, 'user': user, 'files': files, 'owner': owner})


def download(request, file_name):
    file_path = settings.MEDIA_ROOT + '/' + file_name
    file_wrapper = FileWrapper(open(file_path, 'rb'))
    file_mimetype = mimetypes.guess_type(file_path)
    print(file_mimetype)
    print((file_wrapper))
    response = HttpResponse(file_wrapper, content_type=file_mimetype)
    response['X-Sendfile'] = file_path
    response['Content-Disposition'] = 'attachment; filename="%s"' % smart_str(file_name)

    # f = open(file_path, 'r')
    # myFile = File(f)
    # # print(filename)
    # print("puppies")
    return response



def viewYourReports(request):
    user = request.user
    reports = report.objects.all().filter(username_id=user)
    folders = folder.objects.all().filter(username_id=user)
    return render(request, 'reports/viewYourReports.html', {'reports':reports, 'user': user, 'folders':folders })


def editReport(request):
    user = request.user
    title = request.POST.get("title")
    short = request.POST.get("short")
    detailed = request.POST.get("detailed")
    is_private = request.POST.get("private")
    original = request.POST.get("original")
    if(request.POST.getlist('updated')):
        reports = report.objects.get(title=original)
        reports.title = title
        reports.short_description = short
        reports.detailed_description = detailed
        if is_private == "private":
            reports.is_private = True
        else:
            reports.is_private = False

        #reports.is_private = is_private
        reports.save()

    return render(request, 'reports/editReport.html', {'user': user, 'title': title, 'short': short, 'detailed':detailed, 'private': is_private})



def deleteReport(request):
    user = request.user
    id = request.POST.get("id")
    report.objects.filter(id=id).delete()
    return render(request, 'reports/viewYourReports.html', {'user':user})

@csrf_exempt
def searchReport(request):
    query_string = request.GET.get('q')
    results = report.objects.annotate(
        search=SearchVector('title', 'short_description', 'detailed_description'),
    ).filter(search=query_string).exclude(is_private=True).order_by('timestamp')
    return render(request,'reports/searchReports.html', {'results': results })

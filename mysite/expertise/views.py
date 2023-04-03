from django.shortcuts import render
from django.http import HttpResponse

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)

def index(request):
    #m = Person(name='Moritz').save()
    # s = Person(name='Siavash').save()
    # r = m.advisors.connect(s)
    #ResearchInterest(name='AI').save()
    #ResearchInterest(name='AI').save()
    # Role(name='Programmer').save()
    # Expertise(name='python').save()
    # Institute(name='TUD').save()
    # Faculty(name='ZIH').save()
    # Department(name='CompSci').save()

    #for p in Person.nodes.all():
    #    print(p)
    #return HttpResponse("Hello, world. <h1>hi</h1>You're at the expertise index.")
    context = {

    }
    return render(request, 'expertise/index.html', context)

def edit(request):
    return render(request, 'expertise/edit.html')

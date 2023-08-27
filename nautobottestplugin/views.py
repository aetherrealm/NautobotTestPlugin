# views.py
from django.http import HttpResponseRedirect
from formtools.wizard.views import SessionWizardView

class VLANWizard(SessionWizardView):
    def done(self, form_list, **kwargs):
        return HttpResponseRedirect('/page-to-redirect-to-when-done/')
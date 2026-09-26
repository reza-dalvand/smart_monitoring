from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from .forms import CustomAuthenticationForm

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        role_redirects = {
            'country_admin': 'national:dashboard',
            'province_admin': 'province:dashboard',
            'district_admin': 'district:dashboard',
            'principal': 'school:principal_dashboard',
            'assistant': 'school:assistant_dashboard',
            'teacher': 'teacher:dashboard',
        }
        redirect_name = role_redirects.get(user.role, 'dashboard:home')
        try:
            from django.urls import reverse
            return reverse(redirect_name)
        except Exception:
            from django.urls import reverse_lazy
            return str(reverse_lazy('dashboard:home'))

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')
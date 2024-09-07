from admin_app. models import UserProfile

def profile_context(request):
    if request.user.is_authenticated:
        # Check if a UserProfile exists for the authenticated user
        profile_exists = UserProfile.objects.filter(user=request.user).exists()
        
        # If no profile exists, we expect this part to run
        if not profile_exists:
            print(f'No profile found for user: {request.user.username}')
    else:
        profile_exists = False
        print('User is not authenticated')
    return {'profile_exists': profile_exists}

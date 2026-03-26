from base.interfaces.user import IUserRepository
from base.interfaces.session import ISessionRepository
from admins.dto.auth import LoginDTO, SessionDTO
from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed

class AuthService:

    #define the repository here
    def __init__(self, user_repo: IUserRepository, session_repo: ISessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo



    #login method
    def login(self, credetials: LoginDTO, session_info: SessionDTO):
        #get user credetials
        user = self.user_repo.get_by_username(credetials.username)

        #check if the user exists or not
        if not user:
            raise Http404("User not found")
        
        #check if the credentials are correct or not
        if not user.check_password(credetials.password):
            raise AuthenticationFailed("Invalid Credentials")
        
        #pass the user to update last seeon
        self.user_repo.update_last_seen(user)

        #generate the seesion token here
        session = self.session_repo.create(
            user=user,
            ip=session_info.ip_address,
            ua=session_info.user_agent,
            device=session_info.device
    )

        return session
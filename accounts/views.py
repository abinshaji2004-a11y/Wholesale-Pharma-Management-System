from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, OTPVerification
from .serializers import UserSerializer, LoginSerializer
from django.db.models import Q
import random

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created successfully. Pending OTP verification/Admin approval."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            
            if user:
                if user.role == 'dealer':
                    if hasattr(user, 'profile') and user.profile.approval_status != 'approved':
                        return Response({'error': 'Your account is pending admin approval or has been rejected.'}, status=status.HTTP_403_FORBIDDEN)
                        
                tokens = get_tokens_for_user(user)
                return Response({'tokens': tokens, 'role': user.role, 'username': user.username})
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
        
    def put(self, request):
        user = request.user
        new_username = request.data.get('username')
        
        if new_username and new_username != user.username:
            if user.role != 'admin':
                if user.has_changed_username:
                    return Response({'username': ['Username can only be changed once.']}, status=status.HTTP_400_BAD_REQUEST)
                if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                    return Response({'username': ['This username is already taken.']}, status=status.HTTP_400_BAD_REQUEST)
                user.username = new_username
                user.has_changed_username = True
                user.save()
            else:
                if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                    return Response({'username': ['This username is already taken.']}, status=status.HTTP_400_BAD_REQUEST)
                user.username = new_username
                user.save()
                
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminPendingDealersView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get users with role dealer whose profile is pending
        dealers = User.objects.filter(role='dealer', profile__approval_status='pending')
        serializer = UserSerializer(dealers, many=True)
        return Response(serializer.data)

class AdminDealerApprovalView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            dealer = User.objects.get(id=user_id, role='dealer')
            action = request.data.get('action') # 'approve' or 'reject'
            credit_limit = request.data.get('credit_limit', 0.00)

            if action == 'approve':
                dealer.profile.approval_status = 'approved'
                dealer.profile.is_verified = True
                dealer.profile.credit_limit = credit_limit
            elif action == 'reject':
                dealer.profile.approval_status = 'rejected'
                dealer.profile.is_verified = False
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            dealer.profile.save()
            return Response({'message': f'Dealer {action}d successfully'})
        except User.DoesNotExist:
            return Response({'error': 'Dealer not found'}, status=status.HTTP_404_NOT_FOUND)

class AdminUserUsernameUpdateView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        q = request.query_params.get('q', '')
        users = User.objects.filter(role__in=['customer', 'dealer'])
        if q:
            users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        
        users = users[:20]
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_user = User.objects.get(id=user_id)
            
            username = request.data.get('username')
            email = request.data.get('email')
            first_name = request.data.get('first_name', '')
            last_name = request.data.get('last_name', '')
            phone_number = request.data.get('phone_number', '')
            
            if username and username != target_user.username:
                if User.objects.filter(username=username).exclude(id=user_id).exists():
                    return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)
                target_user.username = username
                
            if email:
                target_user.email = email
                
            target_user.first_name = first_name
            target_user.last_name = last_name
            target_user.phone_number = phone_number
            target_user.save()
            
            credit_limit = request.data.get('credit_limit')
            address = request.data.get('address')
            
            if hasattr(target_user, 'profile'):
                profile = target_user.profile
                if credit_limit is not None:
                    profile.credit_limit = credit_limit
                if address is not None:
                    profile.address = address
                profile.save()
                
            return Response({'message': 'Profile updated successfully'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

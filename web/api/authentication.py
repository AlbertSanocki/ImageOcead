from rest_framework.authentication import TokenAuthentication as BaseTokenAuth

class TokenAuthentication(BaseTokenAuth):
    """TokenAuthentication defined as Bearer"""
    keyword = 'Bearer'
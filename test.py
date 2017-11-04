



if __name__=='__main__':
    import sys
    sys.path.append('.')
    import storage
    ats = storage.AzureTableStorage()
    user = 'Matt'
    print(ats.get_user_points_used(user))

# Spore API

To create the db:

```
dokku plugin:install https://github.com/dokku/dokku-postgres.git
dokku postgres:create spore_db
dokku postgres:expose spore_db
dokku postgres:info spore_db #copy the username and password and add it to your .env file
```

## Version History

### v0.0.4
- Upgraded to postgres DB on a remote location
- Indexes all `Bought` events, searches for the price of all NFTs
- When you call `last-indexed` in the api, it will tell you the latest synced block 

### v0.0.3
- Returns a GET response from the Flask database
- Uses an .env file to protect the IP and password of the database

### v0.0.2
- Connects to the database

### v0.0.1
- Returns "Hello"
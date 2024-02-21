# SporeAPI™

To create the db:

```
dokku plugin:install https://github.com/dokku/dokku-postgres.git
dokku postgres:create spore_db
dokku postgres:expose spore_db
dokku postgres:info spore_db #copy the username and password and add it to your .env file
```

## To run this project

  1. **Install the required packages** The Spore Api runs in a flask app using python 3.10, for installing the required packages install pip first and run:
       ```
       pip install -r requirements.txt
       ```
  2. **Running the Spore API**:
     - Navigate to the cloned `spore-api` directory.
     - Run the API using Python version 3.10.9:
       ```
       python spore-api.py
       ```
  3. **Environment Configuration**:
     - Rename the `.env.example` file to `.env`.
     - Ensure the following lines exist in the `.env` file to point to your local/remote Postgres instance:
       ```
        host=127.0.0.0
        user=postgres
        password=c747327472jfhhfsdhhhfhehfhkh8777
        port=69420
       ```
    - Note: I havent tested what happens if the DB is not deployed, I added some 500 responses but cant assure it will work, but even an empty database will suffice.
## Version History

### v0.0.5
- Migrated CMC/CG api calls to this application
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
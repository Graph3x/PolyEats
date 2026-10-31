CREATE ROLE address LOGIN PASSWORD 'address';
CREATE DATABASE address OWNER address;
REVOKE CONNECT ON DATABASE address FROM PUBLIC;

CREATE ROLE "user" LOGIN PASSWORD 'user';
CREATE DATABASE "user" OWNER "user";
REVOKE CONNECT ON DATABASE "user" FROM PUBLIC;

CREATE ROLE restaurant LOGIN PASSWORD 'restaurant';
CREATE DATABASE restaurant OWNER restaurant;
REVOKE CONNECT ON DATABASE restaurant FROM PUBLIC;

\c address
SET ROLE address;
\i /schemas/address.sql

\c user
SET ROLE "user";
\i /schemas/user.sql

\c restaurant
SET ROLE restaurant;
\i /schemas/restaurant.sql

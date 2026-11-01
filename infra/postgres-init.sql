CREATE ROLE address LOGIN PASSWORD 'address';
CREATE DATABASE address OWNER address;
REVOKE CONNECT ON DATABASE address FROM PUBLIC;

CREATE ROLE "user" LOGIN PASSWORD 'user';
CREATE DATABASE "user" OWNER "user";
REVOKE CONNECT ON DATABASE "user" FROM PUBLIC;

CREATE ROLE restaurant LOGIN PASSWORD 'restaurant';
CREATE DATABASE restaurant OWNER restaurant;
REVOKE CONNECT ON DATABASE restaurant FROM PUBLIC;

CREATE ROLE account LOGIN PASSWORD 'account';
CREATE DATABASE account OWNER account;
REVOKE CONNECT ON DATABASE account FROM PUBLIC;

CREATE ROLE "courier-profile" LOGIN PASSWORD 'courier-profile';
CREATE DATABASE "courier-profile" OWNER "courier-profile";
REVOKE CONNECT ON DATABASE "courier-profile" FROM PUBLIC;

CREATE ROLE review LOGIN PASSWORD 'review';
CREATE DATABASE review OWNER review;
REVOKE CONNECT ON DATABASE review FROM PUBLIC;

\c address
SET ROLE address;
\i /schemas/address.sql

\c user
SET ROLE "user";
\i /schemas/user.sql

\c restaurant
SET ROLE restaurant;
\i /schemas/restaurant.sql

\c account
SET ROLE account;
\i /schemas/account.sql

\c courier-profile
SET ROLE "courier-profile";
\i /schemas/courier-profile.sql

\c review
SET ROLE review;
\i /schemas/review.sql

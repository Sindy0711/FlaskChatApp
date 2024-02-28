CREATE TABLE Users (
  UserID SERIAL PRIMARY KEY,
  firstName VARCHAR NOT NULL,
  lastName VARCHAR NOT NULL,
  email VARCHAR UNIQUE NOT NULL,
  password VARCHAR NOT NULL
);

CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_code VARCHAR NOT NULL,
    members INTEGER NOT NULL,
    messages JSONB
);

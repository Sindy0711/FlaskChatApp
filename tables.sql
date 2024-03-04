
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  email VARCHAR UNIQUE NOT NULL,
  password VARCHAR NOT NULL
);
CREATE TABLE rooms (
  id SERIAL PRIMARY KEY,
  code VARCHAR(6) UNIQUE NOT NULL,
  members INTEGER DEFAULT 0
);


CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    content VARCHAR(200),
    room_id INTEGER NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE TABLE joins (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  room_id INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (room_id) REFERENCES rooms(id)
);

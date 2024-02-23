CREATE TABLE clients (
	id SERIAL PRIMARY KEY,
	limits INTEGER NOT NULL, 
	initial_balance INTEGER NOT NULL, 
	actual_balance INTEGER NOT NULL
);

CREATE TABLE transactions (
	id SERIAL PRIMARY KEY,
	value INTEGER NOT NULL,
	transaction_type CHAR(1) NOT NULL,
	description VARCHAR(10) NOT NULL,
	completed_at TIMESTAMP NOT NULL DEFAULT NOW(),
	client_id INTEGER NOT NULL,
	CONSTRAINT fk_clientes_saldos_id
		FOREIGN KEY (client_id) REFERENCES clients(id)
);

DO $$
BEGIN
  INSERT INTO clients (id, limits, initial_balance, actual_balance)
  VALUES (1, 1000 * 100, 0, 0),
    (2, 800 * 100, 0, 0),
    (3, 10000 * 100, 0, 0),
    (4, 100000 * 100, 0, 0),
    (5, 5000 * 100, 0, 0);
END;
$$

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL
);

INSERT INTO usuarios (id, nombre, email)
VALUES
    (1, 'Juan Steban Riveros Orozco', 'juanstebanriveros@gmail.com'),
    (2, 'Usuario de Prueba ADSO', 'prueba@example.com')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre), email = VALUES(email);
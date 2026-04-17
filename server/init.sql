-- 1. Tabel Lokasi Penyimpanan (5 rows, 1 kolom)
CREATE TABLE storage_locations (
    id SERIAL PRIMARY KEY,
    row_position INT NOT NULL CHECK (row_position IN (1, 2, 3, 4, 5)) UNIQUE,
    location_code VARCHAR(10) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabel Komponen/Barang
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,            
    sku VARCHAR(50) UNIQUE NOT NULL,       
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    stock_quantity INT NOT NULL DEFAULT 0,
    description VARCHAR(500),
    image_url VARCHAR(500),
    location_id INT REFERENCES storage_locations(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabel Log Eksekusi
CREATE TABLE dispense_logs (
    id SERIAL PRIMARY KEY,
    item_id INT REFERENCES items(id) ON DELETE CASCADE,
    requested_qty INT NOT NULL DEFAULT 1,
    source VARCHAR(20) NOT NULL,           
    status VARCHAR(20) NOT NULL,           
    error_message TEXT,                    -- Tetap dipertahankan karena error log sangat penting untuk debugging hardware
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexing
CREATE INDEX idx_items_sku ON items(sku);
CREATE INDEX idx_logs_status ON dispense_logs(status);

-- ===== SAMPLE DATA =====
-- 1. Masukkan Storage Locations (5 rows universal)
INSERT INTO storage_locations (row_position, location_code) VALUES 
(1, 'ROW1'), (2, 'ROW2'), (3, 'ROW3'), (4, 'ROW4'), (5, 'ROW5');

-- 2. Masukkan 5 Produk (1 per row)
INSERT INTO items (name, sku, price, stock_quantity, location_id, description, image_url) VALUES
-- Row 1: Bayam
('Bayam Segar', 'SKU001', 15000, 50, 1, 'Bayam organik pilihan, kaya zat besi dan vitamin A. Cocok untuk salad atau tumis-tumisan.', ''),

-- Row 2: Wortel
('Wortel Premium', 'SKU002', 12000, 40, 2, 'Wortel segar merah cerah dengan rasa manis alami. Sempurna untuk makanan sehat dan jus.', ''),

-- Row 3: Brokoli
('Brokoli Organik', 'SKU003', 18000, 30, 3, 'Brokoli hijau segar penuh nutrisi. Mengandung vitamin C tinggi dan serat untuk kesehatan optimal.', ''),

-- Row 4: Beras
('Beras Premium 5kg', 'SKU004', 65000, 25, 4, 'Beras putih pilihan premium berkualitas tinggi. Butir panjang, nasi pulen, aman dan higienis.', ''),

-- Row 5: Minyak Goreng
('Minyak Goreng 2L', 'SKU005', 28000, 40, 5, 'Minyak goreng berkualitas tinggi, cocok untuk semua jenis masakan. Tahan lama dan hemat.', '');
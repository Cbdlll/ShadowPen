require 'sinatra'
require 'sqlite3'
require 'json'

# 强制刷新 STDOUT，确保 Docker 日志能实时显示
$stdout.sync = true

# Configure Sinatra
set :bind, '0.0.0.0'
set :port, 4567
set :public_folder, 'public'
set :views, 'views'

puts "=== Initializing Gallery Application ==="

# Initialize Database
begin
  DB = SQLite3::Database.new "gallery.db"
  DB.results_as_hash = true
  puts "✓ Database connection established"
rescue => e
  puts "✗ Database connection failed: #{e.message}"
  raise
end

# Create Tables
begin
  DB.execute <<-SQL
    CREATE TABLE IF NOT EXISTS photos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT,
      description TEXT,
      camera_model TEXT,
      filename TEXT
    );
  SQL
  puts "✓ Photos table ready"

  DB.execute <<-SQL
    CREATE TABLE IF NOT EXISTS guestbook (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      message TEXT
    );
  SQL
  puts "✓ Guestbook table ready"
rescue => e
  puts "✗ Table creation failed: #{e.message}"
  raise
end

# 清空并重新插入数据（测试环境，每次启动都重置）
begin
  puts "Clearing existing data..."
  DB.execute("DELETE FROM photos")
  DB.execute("DELETE FROM guestbook")
  puts "✓ Database cleared"
  
  puts "Starting photo seeding process..."
  mock_photos = [
    ["Urban Life", "Busy city streets at night.", "Sony A7III", "https://placehold.co/800x600?text=Urban+Life"],
    ["Coffee Time", "A relaxing cup of coffee.", "Fujifilm X-T4", "https://placehold.co/800x600?text=Coffee+Time"],
    ["Coding Session", "Late night coding marathon.", "MacBook Pro Webcam", "https://placehold.co/800x600?text=Coding"],
    ["Abstract Art", "Colorful abstract patterns.", "Leica Q2", "https://placehold.co/800x600?text=Abstract"],
    ["Vintage Car", "Classic 1960s mustang.", "Nikon D850", "https://placehold.co/800x600?text=Vintage+Car"],
    ["Forest Walk", "Peaceful trail in the woods.", "Canon EOS R6", "https://placehold.co/800x600?text=Forest"],
    ["Ocean Waves", "Crashing waves on the shore.", "GoPro Hero 10", "https://placehold.co/800x600?text=Ocean"],
    ["Desert Dunes", "Golden sand dunes at sunset.", "Sony A7R IV", "https://placehold.co/800x600?text=Desert"],
    ["Street Food", "Delicious local street food.", "iPhone 13 Pro", "https://placehold.co/800x600?text=Food"],
    ["Architecture", "Modern building facade.", "Canon 5D Mark IV", "https://placehold.co/800x600?text=Architecture"],
    ["Portrait", "Studio portrait session.", "Hasselblad X1D", "https://placehold.co/800x600?text=Portrait"],
    ["Wildlife", "Lion in the savannah.", "Nikon Z9", "https://placehold.co/800x600?text=Wildlife"],
    ["Macro Flower", "Close up of a blooming rose.", "Sony 90mm Macro", "https://placehold.co/800x600?text=Flower"],
    ["Night Sky", "Starry night and milky way.", "Canon EOS Ra", "https://placehold.co/800x600?text=Night+Sky"],
    ["Concert", "Live music performance.", "Sony A7S III", "https://placehold.co/800x600?text=Concert"],
    ["Travel", "Passport and map on table.", "Fujifilm X100V", "https://placehold.co/800x600?text=Travel"],
    ["Sunset", "Beautiful sunset at the beach.", "Canon EOS R5", "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?auto=format&fit=crop&w=800&q=80"],
    ["Mountain", "Snowy peaks.", "Nikon Z9", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80"]
  ]

  # 使用事务确保数据完整性
  DB.transaction do
    mock_photos.each_with_index do |photo, index|
      DB.execute("INSERT INTO photos (title, description, camera_model, filename) VALUES (?, ?, ?, ?)", photo)
      puts "  ✓ Inserted photo #{index + 1}/#{mock_photos.length}: #{photo[0]}"
    end
  end
  
  # 插入 guestbook 初始数据
  DB.execute("INSERT INTO guestbook (name, message) VALUES (?, ?)", ["Alice", "Great photos!"])
  DB.execute("INSERT INTO guestbook (name, message) VALUES (?, ?)", ["Bob", "Amazing collection!"])
  
  # 验证插入结果
  photo_count = DB.execute("SELECT count(*) FROM photos")[0][0]
  guestbook_count = DB.execute("SELECT count(*) FROM guestbook")[0][0]
  puts "✓ Successfully seeded #{photo_count} photos and #{guestbook_count} guestbook entries"
rescue => e
  puts "✗ Data seeding failed: #{e.message}"
  puts "  Backtrace: #{e.backtrace.first(3).join("\n  ")}"
  raise
end

puts "=== Application Ready ==="

# Global User Profile (Simulated Session)
$user_profile = {
  website: "https://example.com"
}

# Helpers
helpers do
  def h(text)
    # INTENTIONALLY BROKEN: No escaping for XSS demonstration
    text
  end
end

# Routes

# 1. Gallery (Home)
get '/' do
  @photos = DB.execute("SELECT * FROM photos ORDER BY id DESC")
  @msg = params[:msg] # Vuln #1: Reflected
  @tag = params[:tag] # Vuln #5: Reflected
  erb :index
end

# Upload Photo (Simulated)
post '/upload' do
  title = params[:title]
  desc = params[:description]
  camera = params[:camera_model]
  filename = params[:filename] || "https://via.placeholder.com/800"
  
  # Vuln #2, #3, #4: Stored XSS in Title, Description, Camera Model
  DB.execute("INSERT INTO photos (title, description, camera_model, filename) VALUES (?, ?, ?, ?)", [title, desc, camera, filename])
  
  redirect '/?msg=Photo uploaded successfully!'
end

# 2. Guestbook
get '/guestbook' do
  @entries = DB.execute("SELECT * FROM guestbook ORDER BY id DESC")
  erb :guestbook
end

post '/guestbook' do
  name = params[:name]
  message = params[:message]
  
  # Vuln #6, #7: Stored XSS in Name, Message
  DB.execute("INSERT INTO guestbook (name, message) VALUES (?, ?)", [name, message])
  
  redirect '/guestbook'
end

# 3. Search
get '/search' do
  @query = params[:q]
  # Vuln #8: Reflected XSS in Search Query
  if @query
    @results = DB.execute("SELECT * FROM photos WHERE title LIKE ? OR description LIKE ?", ["%#{@query}%", "%#{@query}%"])
  end
  erb :search
end

# 4. Profile
get '/profile' do
  @website = $user_profile[:website]
  erb :profile
end

post '/profile' do
  # Vuln #9: Javascript Protocol XSS
  $user_profile[:website] = params[:website]
  redirect '/profile?msg=Profile updated!'
end

# 5. Help Center (DOM XSS)
get '/faq' do
  erb :faq
end

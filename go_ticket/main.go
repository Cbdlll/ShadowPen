package main

import (
	"html/template"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// --- Models ---

type Ticket struct {
	ID          uint `gorm:"primaryKey"`
	Subject     string
	Description string
	Priority    string // Low, Medium, High
	Status      string // Open, Closed
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Comments    []Comment
}

type Comment struct {
	ID        uint `gorm:"primaryKey"`
	TicketID  uint
	Author    string
	Content   string
	CreatedAt time.Time
}

type AccessLog struct {
	ID        uint `gorm:"primaryKey"`
	UserAgent string
	Path      string
	CreatedAt time.Time
}

// --- Database ---

var db *gorm.DB

func initDB() {
	var err error
	db, err = gorm.Open(sqlite.Open("tickets.db"), &gorm.Config{})
	if err != nil {
		panic("failed to connect database")
	}
	db.AutoMigrate(&Ticket{}, &Comment{}, &AccessLog{})

	// Seed data if empty
	var count int64
	db.Model(&Ticket{}).Count(&count)
	if count == 0 {
		// Ticket 1: Login Issue
		db.Create(&Ticket{
			Subject:     "Cannot login",
			Description: "I forgot my password and the reset link is not working. I've tried multiple times but haven't received any email.",
			Priority:    "High",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-48 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "Have you checked your spam folder? The reset email might have been filtered.", CreatedAt: time.Now().Add(-47 * time.Hour)},
				{Author: "john.doe", Content: "Yes, I checked spam folder but nothing there. Can you resend?", CreatedAt: time.Now().Add(-24 * time.Hour)},
			},
		})
		
		// Ticket 2: Feature Request
		db.Create(&Ticket{
			Subject:     "Feature request: Dark mode",
			Description: "Please add dark mode to the app. It would be great for users who work late at night.",
			Priority:    "Low",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-72 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "Thank you for your suggestion! We've added this to our roadmap.", CreatedAt: time.Now().Add(-70 * time.Hour)},
				{Author: "jane.smith", Content: "I second this! Dark mode would be amazing.", CreatedAt: time.Now().Add(-50 * time.Hour)},
			},
		})
		
		// Ticket 3: Bug Report
		db.Create(&Ticket{
			Subject:     "Payment processing error",
			Description: "When I try to complete a payment, I get an error message saying 'Transaction failed'. This happens every time I try to pay.",
			Priority:    "High",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-12 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "We're investigating this issue. Can you provide your transaction ID?", CreatedAt: time.Now().Add(-10 * time.Hour)},
			},
		})
		
		// Ticket 4: Account Issue
		db.Create(&Ticket{
			Subject:     "Account locked after multiple failed attempts",
			Description: "My account has been locked after I entered the wrong password a few times. How can I unlock it?",
			Priority:    "Medium",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-6 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "Your account will be automatically unlocked after 30 minutes. Alternatively, you can use the password reset feature.", CreatedAt: time.Now().Add(-5 * time.Hour)},
			},
		})
		
		// Ticket 5: Closed Ticket
		db.Create(&Ticket{
			Subject:     "Email notifications not working",
			Description: "I'm not receiving email notifications for ticket updates. I've checked my email settings and everything looks correct.",
			Priority:    "Medium",
			Status:      "Closed",
			CreatedAt:   time.Now().Add(-120 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "We found the issue - your email was marked as unverified. Please verify your email address.", CreatedAt: time.Now().Add(-118 * time.Hour)},
				{Author: "user123", Content: "Thank you! I've verified my email and notifications are working now.", CreatedAt: time.Now().Add(-100 * time.Hour)},
				{Author: "Support", Content: "Great! I'm closing this ticket. If you encounter any other issues, please let us know.", CreatedAt: time.Now().Add(-99 * time.Hour)},
			},
		})
		
		// Ticket 6: API Issue
		db.Create(&Ticket{
			Subject:     "API rate limit too restrictive",
			Description: "The API rate limit of 100 requests per hour is too low for our integration. Can we get it increased?",
			Priority:    "Medium",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-36 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "We can increase the rate limit for enterprise accounts. Would you like to upgrade?", CreatedAt: time.Now().Add(-35 * time.Hour)},
			},
		})
		
		// Ticket 7: UI Bug
		db.Create(&Ticket{
			Subject:     "Mobile view layout broken",
			Description: "On mobile devices, the ticket list table is not responsive and text overlaps. This makes it impossible to read ticket subjects.",
			Priority:    "High",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-18 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "Thank you for reporting this. Our development team is working on a fix.", CreatedAt: time.Now().Add(-16 * time.Hour)},
				{Author: "dev.team", Content: "Fix deployed. Please refresh and let us know if the issue persists.", CreatedAt: time.Now().Add(-2 * time.Hour)},
			},
		})
		
		// Ticket 8: Feature Request
		db.Create(&Ticket{
			Subject:     "Request: Export tickets to CSV",
			Description: "It would be very helpful if we could export our tickets to CSV format for reporting purposes.",
			Priority:    "Low",
			Status:      "Open",
			CreatedAt:   time.Now().Add(-96 * time.Hour),
			Comments: []Comment{
				{Author: "Support", Content: "This feature is planned for our next release. Stay tuned!", CreatedAt: time.Now().Add(-94 * time.Hour)},
			},
		})
	}
}

// --- Helpers ---

// Unsafe rendering function to bypass Go's auto-escaping
func unsafe(v interface{}) template.HTML {
	if v == nil {
		return template.HTML("")
	}
	switch val := v.(type) {
	case string:
		return template.HTML(val)
	case template.HTML:
		return val
	default:
		return template.HTML("")
	}
}

// --- Controllers ---

func main() {
	initDB()

	r := gin.Default()

	// Load templates with custom functions
	r.SetFuncMap(template.FuncMap{
		"unsafe": unsafe,
	})
	r.LoadHTMLGlob("templates/*")

	// Middleware to log requests (Vulnerability 8: Stored XSS in Logs)
	r.Use(func(c *gin.Context) {
		userAgent := c.GetHeader("User-Agent")
		db.Create(&AccessLog{
			UserAgent: userAgent,
			Path:      c.Request.URL.Path,
			CreatedAt: time.Now(),
		})
		c.Next()
	})

	// Routes

	// 1. Home / Dashboard
	r.GET("/", func(c *gin.Context) {
		// Vulnerability 5: User Profile/Header (simulated via cookie or query)
		username, _ := c.Cookie("username")
		// Keep username empty if not logged in (don't set to "Guest")
		// This allows templates to properly show login/logout buttons
		
		var tickets []Ticket
		db.Find(&tickets)
		c.HTML(http.StatusOK, "index.html", gin.H{
			"Title":    "Dashboard",
			"Username": username, // XSS if username is manipulated
			"Tickets":  tickets,
		})
	})

	// 2. Login (Vulnerability 7: Reflected XSS via Redirect)
	r.GET("/login", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		redirect := c.Query("redirect")
		c.HTML(http.StatusOK, "login.html", gin.H{
			"Title":    "Login",
			"Redirect": redirect, // XSS
			"Username": username,
		})
	})

	r.POST("/login", func(c *gin.Context) {
		username := c.PostForm("username")
		if username == "" {
			username = "Guest"
		}
		// Set cookie with 1 hour expiration
		c.SetCookie("username", username, 3600, "/", "", false, false)
		redirect := c.PostForm("redirect")
		// Validate redirect URL to prevent open redirect (basic check)
		if redirect != "" && redirect[0] == '/' {
			c.Redirect(http.StatusFound, redirect)
		} else {
			c.Redirect(http.StatusFound, "/")
		}
	})

	r.GET("/logout", func(c *gin.Context) {
		// Clear the username cookie by setting it to empty with max age -1
		c.SetCookie("username", "", -1, "/", "", false, false)
		// Redirect to home page after logout
		c.Redirect(http.StatusFound, "/")
	})

	// 3. Ticket List (Vulnerability 10: Reflected XSS in Filter/Pagination)
	r.GET("/tickets", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		filter := c.Query("filter")
		var tickets []Ticket
		query := db.Model(&Ticket{})
		if filter != "" {
			query = query.Where("subject LIKE ?", "%"+filter+"%")
		}
		query.Find(&tickets)

		c.HTML(http.StatusOK, "ticket_list.html", gin.H{
			"Title":    "All Tickets",
			"Tickets":  tickets,
			"Filter":   filter, // XSS
			"Username": username,
		})
	})

	// 4. Create Ticket
	r.POST("/tickets", func(c *gin.Context) {
		subject := c.PostForm("subject")
		description := c.PostForm("description")
		priority := c.PostForm("priority")

		ticket := Ticket{
			Subject:     subject,
			Description: description,
			Priority:    priority,
			Status:      "Open",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		}
		db.Create(&ticket)
		c.Redirect(http.StatusFound, "/")
	})

	// 5. Ticket Detail (Vulnerability 1, 2, 3, 4)
	r.GET("/tickets/:id", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		var ticket Ticket
		ticketID := c.Param("id")
		
		// Validate ticket ID and fetch ticket with comments
		if err := db.Preload("Comments").First(&ticket, ticketID).Error; err != nil {
			c.Redirect(http.StatusFound, "/error?msg=Ticket+not+found")
			return
		}

		c.HTML(http.StatusOK, "ticket_detail.html", gin.H{
			"Title":    "Ticket #" + ticketID,
			"Ticket":   ticket,
			"Username": username,
		})
	})

	// 6. Add Comment (Vulnerability 4: Stored XSS in Chat)
	r.POST("/tickets/:id/chat", func(c *gin.Context) {
		content := c.PostForm("content")
		username, _ := c.Cookie("username")
		if username == "" {
			username = "Anonymous"
		}

		ticketID := c.Param("id")
		var ticket Ticket
		if err := db.First(&ticket, ticketID).Error; err != nil {
			c.Redirect(http.StatusFound, "/error?msg=Ticket+not+found")
			return
		}

		// Only create comment if content is not empty
		if content != "" {
			comment := Comment{
				TicketID:  ticket.ID,
				Author:    username,
				Content:   content,
				CreatedAt: time.Now(),
			}
			db.Model(&ticket).Association("Comments").Append(&comment)
		}
		
		c.Redirect(http.StatusFound, "/tickets/"+ticketID)
	})

	// 7. Search (Vulnerability 6: Reflected XSS)
	r.GET("/search", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		q := c.Query("q")
		var tickets []Ticket
		if q != "" {
			db.Where("subject LIKE ? OR description LIKE ?", "%"+q+"%", "%"+q+"%").Find(&tickets)
		}
		c.HTML(http.StatusOK, "search.html", gin.H{
			"Title":    "Search Results",
			"Query":    q, // XSS
			"Tickets":  tickets,
			"Username": username,
		})
	})

	// 8. Admin Logs (Vulnerability 8: Stored XSS via User-Agent)
	r.GET("/admin/logs", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		var logs []AccessLog
		db.Order("created_at desc").Limit(50).Find(&logs)
		c.HTML(http.StatusOK, "admin_logs.html", gin.H{
			"Title":    "System Logs",
			"Logs":     logs,
			"Username": username,
		})
	})

	// 9. Error Page (Vulnerability 9: Reflected XSS)
	r.GET("/error", func(c *gin.Context) {
		username, _ := c.Cookie("username")
		msg := c.Query("msg")
		c.HTML(http.StatusOK, "error.html", gin.H{
			"Title":    "Error",
			"Msg":      msg, // XSS
			"Username": username,
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	r.Run(":" + port)
}

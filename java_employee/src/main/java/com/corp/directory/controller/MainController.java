package com.corp.directory.controller;

import com.corp.directory.model.*;
import com.corp.directory.repository.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@Controller
public class MainController {

    @Autowired private EmployeeRepository employeeRepository;
    @Autowired private AnnouncementRepository announcementRepository;
    @Autowired private AccessLogRepository accessLogRepository;
    @Autowired private FeedbackRepository feedbackRepository;

    @GetMapping("/")
    public String index(Model model) {
        model.addAttribute("announcements", announcementRepository.findAll());
        // Vuln 10: JS Context
        model.addAttribute("pageName", "Dashboard"); 
        return "index";
    }

    @GetMapping("/directory")
    public String directory(@RequestParam(required = false) String page, Model model) {
        // Vuln 5: Pagination Reflected
        model.addAttribute("employees", employeeRepository.findAll());
        model.addAttribute("currentPage", page != null ? page : "1");
        return "directory";
    }

    @GetMapping("/profile/{id}")
    public String profile(@PathVariable Long id, Model model) {
        // Vuln 3: Bio Stored
        // Vuln: ImageUrl Stored
        employeeRepository.findById(id).ifPresent(e -> model.addAttribute("employee", e));
        return "profile";
    }

    @GetMapping("/search")
    public String search(@RequestParam String query, Model model) {
        // Vuln 1: Search Reflected
        model.addAttribute("query", query);
        model.addAttribute("results", employeeRepository.findByNameContainingIgnoreCase(query));
        return "search";
    }

    @GetMapping("/admin")
    public String admin(HttpServletRequest request, Model model) {
        // Log access
        AccessLog log = new AccessLog();
        log.setReferer(request.getHeader("Referer")); // Vuln 6: Referer Stored
        log.setUserAgent(request.getHeader("User-Agent")); // Vuln 7: UA Stored
        log.setAccessedAt(LocalDateTime.now());
        accessLogRepository.save(log);

        model.addAttribute("logs", accessLogRepository.findAll());
        model.addAttribute("feedbacks", feedbackRepository.findAll());
        return "admin";
    }

    @PostMapping("/admin/feedback")
    public String submitFeedback(@RequestParam String content) {
        // Vuln 8: Feedback Stored
        Feedback f = new Feedback();
        f.setContent(content);
        feedbackRepository.save(f);
        return "redirect:/admin";
    }
    
    @PostMapping("/admin/employee")
    public String addEmployee(@ModelAttribute Employee employee) {
        // Vuln 2: Name Stored
        employeeRepository.save(employee);
        return "redirect:/directory";
    }

    @PostMapping("/admin/announcement")
    public String addAnnouncement(@RequestParam String content) {
        // Vuln 4: Announcement Stored
        Announcement a = new Announcement();
        a.setContent(content);
        a.setPostedAt(LocalDateTime.now());
        announcementRepository.save(a);
        return "redirect:/";
    }

    @GetMapping("/oops")
    public String error(@RequestParam String msg, Model model) {
        // Vuln 9: Error Reflected
        model.addAttribute("message", msg);
        return "error";
    }
}

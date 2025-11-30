package com.corp.directory.config;

import com.corp.directory.model.Announcement;
import com.corp.directory.model.Employee;
import com.corp.directory.repository.AnnouncementRepository;
import com.corp.directory.repository.EmployeeRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDateTime;

@Configuration
public class DataInitializer {

    @Bean
    public CommandLineRunner initData(EmployeeRepository employeeRepository, AnnouncementRepository announcementRepository) {
        return args -> {
            Employee e1 = new Employee();
            e1.setName("Alice Smith");
            e1.setPosition("Software Engineer");
            e1.setBio("Loves <b>coding</b> and coffee.");
            e1.setImageUrl("https://via.placeholder.com/150");
            e1.setEmail("alice@corp.com");
            employeeRepository.save(e1);

            Employee e2 = new Employee();
            e2.setName("Bob Jones");
            e2.setPosition("Product Manager");
            e2.setBio("Focused on user experience.");
            e2.setImageUrl("https://via.placeholder.com/150");
            e2.setEmail("bob@corp.com");
            employeeRepository.save(e2);

            Employee e3 = new Employee();
            e3.setName("Charlie Brown");
            e3.setPosition("UI/UX Designer");
            e3.setBio("Designs beautiful interfaces.");
            e3.setImageUrl("https://via.placeholder.com/150");
            e3.setEmail("charlie@corp.com");
            employeeRepository.save(e3);

            Employee e4 = new Employee();
            e4.setName("Diana Prince");
            e4.setPosition("Project Manager");
            e4.setBio("Keeps projects on track.");
            e4.setImageUrl("https://via.placeholder.com/150");
            e4.setEmail("diana@corp.com");
            employeeRepository.save(e4);

            Employee e5 = new Employee();
            e5.setName("Ethan Hunt");
            e5.setPosition("Security Analyst");
            e5.setBio("Ensures our systems are secure.");
            e5.setImageUrl("https://via.placeholder.com/150");
            e5.setEmail("ethan@corp.com");
            employeeRepository.save(e5);

            Announcement a1 = new Announcement();
            a1.setContent("Welcome to the new <i>Employee Directory</i>!");
            a1.setPostedAt(LocalDateTime.now());
            announcementRepository.save(a1);

            Announcement a2 = new Announcement();
            a2.setContent("The new coffee machine is now available in the break room.");
            a2.setPostedAt(LocalDateTime.now().minusHours(1));
            announcementRepository.save(a2);

            Employee e6 = new Employee();
            e6.setName("Frank Castle");
            e6.setPosition("HR Specialist");
            e6.setBio("Handles employee relations.");
            e6.setImageUrl("https://via.placeholder.com/150");
            e6.setEmail("frank@corp.com");
            employeeRepository.save(e6);

            Employee e7 = new Employee();
            e7.setName("Grace Hopper");
            e7.setPosition("Lead Developer");
            e7.setBio("Pioneering new technologies.");
            e7.setImageUrl("https://via.placeholder.com/150");
            e7.setEmail("grace@corp.com");
            employeeRepository.save(e7);

            Employee e8 = new Employee();
            e8.setName("Heidi-chan");
            e8.setPosition("QA Tester");
            e8.setBio("Tests everything.");
            e8.setImageUrl("https://via.placeholder.com/150");
            e8.setEmail("heidi@corp.com");
            employeeRepository.save(e8);

            Announcement a3 = new Announcement();
            a3.setContent("Don't forget the company picnic this Friday!");
            a3.setPostedAt(LocalDateTime.now().minusDays(1));
            announcementRepository.save(a3);

            Announcement a4 = new Announcement();
            a4.setContent("The quarterly report is due next Monday.");
            a4.setPostedAt(LocalDateTime.now().minusDays(2));
            announcementRepository.save(a4);
        };
    }
}

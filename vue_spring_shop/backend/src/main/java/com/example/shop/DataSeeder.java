package com.example.shop;

import com.example.shop.model.Review;
import com.example.shop.repository.ReviewRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DataSeeder {

    @Bean
    CommandLineRunner seedData(ReviewRepository reviewRepository) {
        return args -> {
            if (reviewRepository.count() == 0) {
                // Seed a review with seller reply containing XSS
                Review review = new Review();
                review.setProductId(1L);
                review.setAuthor("John Doe");
                review.setTitle("Great Product!");
                review.setContent("I love this laptop. Works perfectly.");
                review.setRating(5);
                review.setSellerReply("Thank you for your feedback! We are glad you like it.");
                reviewRepository.save(review);
            }
        };
    }
}

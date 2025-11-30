package com.example.shop.model;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
public class Review {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long productId;
    private String author;
    private String title;
    
    @Column(length = 1000)
    private String content;
    
    private int rating;
    
    @Column(length = 1000)
    private String sellerReply;
}

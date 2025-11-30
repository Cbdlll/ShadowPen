package com.example.shop.controller;

import com.example.shop.model.Question;
import com.example.shop.repository.QuestionRepository;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/questions")
@CrossOrigin(origins = "*")
public class QuestionController {

    private final QuestionRepository questionRepository;

    public QuestionController(QuestionRepository questionRepository) {
        this.questionRepository = questionRepository;
    }

    @GetMapping("/product/{productId}")
    public List<Question> getQuestions(@PathVariable Long productId) {
        return questionRepository.findByProductId(productId);
    }

    @PostMapping
    public Question addQuestion(@RequestBody Question question) {
        // VULNERABILITY: No sanitization of input
        return questionRepository.save(question);
    }
}

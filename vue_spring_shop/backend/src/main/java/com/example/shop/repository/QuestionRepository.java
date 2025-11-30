package com.example.shop.repository;

import com.example.shop.model.Question;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface QuestionRepository extends JpaRepository<Question, Long> {
    List<Question> findByProductId(Long productId);
}

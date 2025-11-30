package com.example.shop.controller;

import com.example.shop.model.Product;
import com.example.shop.repository.ProductRepository;
import org.springframework.web.bind.annotation.*;
import jakarta.annotation.PostConstruct;
import java.util.List;

@RestController
@RequestMapping("/api/products")
@CrossOrigin(origins = "*")
public class ProductController {

    private final ProductRepository productRepository;

    public ProductController(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @PostConstruct
    public void init() {
        if (productRepository.count() == 0) {
            Product p1 = new Product();
            p1.setName("Gaming Laptop X1");
            p1.setDescription("High performance gaming laptop with RTX 4090.");
            p1.setPrice(2999.99);
            p1.setImageUrl("https://placehold.co/600x400/1a1a1a/ffffff?text=Gaming+Laptop");
            productRepository.save(p1);

            Product p2 = new Product();
            p2.setName("Wireless Headphones");
            p2.setDescription("Noise cancelling over-ear headphones.");
            p2.setPrice(199.99);
            p2.setImageUrl("https://placehold.co/600x400/333333/ffffff?text=Headphones");
            productRepository.save(p2);

            Product p3 = new Product();
            p3.setName("Mechanical Keyboard RGB");
            p3.setDescription("Cherry MX switches with customizable RGB lighting.");
            p3.setPrice(149.99);
            p3.setImageUrl("https://placehold.co/600x400/2c3e50/ffffff?text=Keyboard");
            productRepository.save(p3);

            Product p4 = new Product();
            p4.setName("Wireless Gaming Mouse");
            p4.setDescription("Ergonomic design with 16000 DPI sensor.");
            p4.setPrice(79.99);
            p4.setImageUrl("https://placehold.co/600x400/e74c3c/ffffff?text=Gaming+Mouse");
            productRepository.save(p4);

            Product p5 = new Product();
            p5.setName("4K Monitor 27 inch");
            p5.setDescription("IPS panel with HDR support and 144Hz refresh rate.");
            p5.setPrice(499.99);
            p5.setImageUrl("https://placehold.co/600x400/3498db/ffffff?text=4K+Monitor");
            productRepository.save(p5);

            Product p6 = new Product();
            p6.setName("USB-C Docking Station");
            p6.setDescription("Multi-port hub with power delivery up to 100W.");
            p6.setPrice(129.99);
            p6.setImageUrl("https://placehold.co/600x400/95a5a6/ffffff?text=Docking+Station");
            productRepository.save(p6);

            Product p7 = new Product();
            p7.setName("Webcam 1080p HD");
            p7.setDescription("Full HD webcam with auto-focus and noise reduction.");
            p7.setPrice(89.99);
            p7.setImageUrl("https://placehold.co/600x400/7f8c8d/ffffff?text=Webcam");
            productRepository.save(p7);

            Product p8 = new Product();
            p8.setName("External SSD 1TB");
            p8.setDescription("Portable solid state drive with USB 3.2 Gen 2.");
            p8.setPrice(119.99);
            p8.setImageUrl("https://placehold.co/600x400/27ae60/ffffff?text=SSD");
            productRepository.save(p8);

            Product p9 = new Product();
            p9.setName("Bluetooth Speaker");
            p9.setDescription("Waterproof portable speaker with 20-hour battery life.");
            p9.setPrice(59.99);
            p9.setImageUrl("https://placehold.co/600x400/d35400/ffffff?text=Speaker");
            productRepository.save(p9);

            Product p10 = new Product();
            p10.setName("Laptop Stand Aluminum");
            p10.setDescription("Adjustable ergonomic stand for better posture.");
            p10.setPrice(39.99);
            p10.setImageUrl("https://placehold.co/600x400/bdc3c7/333333?text=Laptop+Stand");
            productRepository.save(p10);

            Product p11 = new Product();
            p11.setName("Wireless Charger Pad");
            p11.setDescription("Fast charging pad compatible with Qi-enabled devices.");
            p11.setPrice(29.99);
            p11.setImageUrl("https://placehold.co/600x400/8e44ad/ffffff?text=Charger");
            productRepository.save(p11);

            Product p12 = new Product();
            p12.setName("Graphics Tablet");
            p12.setDescription("Digital drawing tablet with 8192 pressure levels.");
            p12.setPrice(249.99);
            p12.setImageUrl("https://placehold.co/600x400/16a085/ffffff?text=Graphics+Tablet");
            productRepository.save(p12);

            Product p13 = new Product();
            p13.setName("Smart Watch Pro");
            p13.setDescription("Fitness tracker with heart rate monitor and GPS.");
            p13.setPrice(299.99);
            p13.setImageUrl("https://placehold.co/600x400/2c3e50/ffffff?text=Smart+Watch");
            productRepository.save(p13);

            Product p14 = new Product();
            p14.setName("Desk Lamp LED");
            p14.setDescription("Adjustable brightness with USB charging port.");
            p14.setPrice(45.99);
            p14.setImageUrl("https://placehold.co/600x400/f1c40f/333333?text=Desk+Lamp");
            productRepository.save(p14);

            Product p15 = new Product();
            p15.setName("Cable Management Kit");
            p15.setDescription("Complete set for organizing desk cables and wires.");
            p15.setPrice(19.99);
            p15.setImageUrl("https://placehold.co/600x400/7f8c8d/ffffff?text=Cable+Kit");
            productRepository.save(p15);
        }
    }

    @GetMapping
    public List<Product> getAllProducts() {
        return productRepository.findAll();
    }

    @GetMapping("/{id}")
    public Product getProduct(@PathVariable Long id) {
        return productRepository.findById(id).orElse(null);
    }
}

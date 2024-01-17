# DNS Simulation: Comparative Analysis of Iterative vs. Recursive Resolution

The simulation involves the creation of a DNS system in Python, leveraging object-oriented programming principles to model DNS servers, domain mappings, and resolver strategies. The system simulates the process of resolving domain names to IP addresses, using two distinct strategies: iterative and recursive.

### **Key Components of the Simulation:**

- **DNS Servers:** The simulation includes servers representing the root and top-level domain (TLD), each with its DNS mapping table containing domain-to-IP address mappings.

- **Resolver Strategies:**
  - **Iterative Resolver**: A resolver that queries DNS servers iteratively until it finds the final IP address associated with the requested domain name.

  - **Recursive Resolver**: A resolver that initiates requests to DNS servers and handles any necessary forwarding until it obtains the ultimate IP address for the domain name.
package com.polyeats.courierprofile;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "couriers")
public class Courier extends PanacheEntityBase {

    @Id
    @Column(name = "account_id")
    public String accountId;

    public String name;
    public String vehicle;
    public String status;
}

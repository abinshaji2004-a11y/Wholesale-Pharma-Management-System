/**
 * Hill Climb Car Game - Physics Module
 * Custom 2D rigid body suspension, wheel physics, and terrain height mapping.
 */

class Vector2D {
    constructor(x = 0, y = 0) {
        this.x = x;
        this.y = y;
    }

    set(x, y) {
        this.x = x;
        this.y = y;
        return this;
    }

    add(v) {
        return new Vector2D(this.x + v.x, this.y + v.y);
    }

    sub(v) {
        return new Vector2D(this.x - v.x, this.y - v.y);
    }

    mult(n) {
        return new Vector2D(this.x * n, this.y * n);
    }

    div(n) {
        return new Vector2D(this.x / n, this.y / n);
    }

    dot(v) {
        return this.x * v.x + this.y * v.y;
    }

    cross(v) {
        return this.x * v.y - this.y * v.x;
    }

    lengthSq() {
        return this.x * this.x + this.y * this.y;
    }

    length() {
        return Math.sqrt(this.lengthSq());
    }

    normalize() {
        const len = this.length();
        if (len === 0) return new Vector2D(0, 0);
        return new Vector2D(this.x / len, this.y / len);
    }

    rotate(angle) {
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        return new Vector2D(
            this.x * cos - this.y * sin,
            this.x * sin + this.y * cos
        );
    }

    clone() {
        return new Vector2D(this.x, this.y);
    }
}

class Terrain {
    constructor(type = 'hills') {
        this.type = type;
        this.amplitude1 = 120;
        this.frequency1 = 0.0015;
        this.amplitude2 = 40;
        this.frequency2 = 0.005;
        this.amplitude3 = 10;
        this.frequency3 = 0.02;
        
        this.gravity = -600; // default gravity (pixels/s^2, pointing down, so negative)
        this.friction = 0.8;
        
        this.configureType(type);
    }

    configureType(type) {
        this.type = type;
        if (type === 'desert') {
            // Desert has taller sand dunes and short repetitive bumps
            this.amplitude1 = 160;
            this.frequency1 = 0.001;
            this.amplitude2 = 60;
            this.frequency2 = 0.004;
            this.amplitude3 = 15;
            this.frequency3 = 0.015;
            this.gravity = -600;
            this.friction = 0.65; // sand has lower traction
        } else if (type === 'moon') {
            // Moon has deep craters, low gravity
            this.amplitude1 = 200;
            this.frequency1 = 0.0008;
            this.amplitude2 = 80;
            this.frequency2 = 0.003;
            this.amplitude3 = 5;
            this.frequency3 = 0.01;
            this.gravity = -180; // lunar gravity is ~1/6th of earth
            this.friction = 0.9;  // tires grip well, but low gravity means less normal force
        } else {
            // Hills (Earth)
            this.amplitude1 = 100;
            this.frequency1 = 0.0012;
            this.amplitude2 = 30;
            this.frequency2 = 0.006;
            this.amplitude3 = 8;
            this.frequency3 = 0.025;
            this.gravity = -650;
            this.friction = 0.85;
        }
    }

    // Procedural terrain height at coordinate x
    getHeight(x) {
        if (x < -100) return 0; // Flat start zone
        if (x < 300) {
            // Smooth blend from flat start to hills
            const blend = Math.max(0, x / 300);
            const raw = this.getRawHeight(x);
            return raw * blend - (1 - blend) * 50;
        }
        return this.getRawHeight(x);
    }

    getRawHeight(x) {
        // Multi-frequency noise (cosine wave superposition)
        const h1 = Math.cos(x * this.frequency1) * this.amplitude1;
        const h2 = Math.sin(x * this.frequency2) * this.amplitude2;
        
        // Add occasional big jumps or steps on Hills & Desert, or large craters on Moon
        let feature = 0;
        if (this.type === 'moon') {
            // Moon craters: using a shaped sine wave for steep lips
            feature = Math.sin(x * 0.0005) * 80;
            if (Math.sin(x * 0.002) < -0.6) {
                feature -= 120; // Deep craters
            }
        } else if (this.type === 'desert') {
            // Large dunes
            feature = Math.cos(x * 0.0003) * 100;
        } else {
            // Earth: steep climbing hills
            feature = Math.sin(x * 0.0004) * 80;
        }

        const h3 = Math.cos(x * this.frequency3) * this.amplitude3;
        
        return h1 + h2 + h3 + feature - 150; // offset down so 0 height is slightly below middle
    }

    getNormal(x) {
        const dx = 0.5;
        const y1 = this.getHeight(x - dx);
        const y2 = this.getHeight(x + dx);
        // Tangent vector is (2 * dx, y2 - y1)
        // Normal vector is perpendicular: ( -(y2 - y1), 2 * dx )
        const n = new Vector2D(-(y2 - y1), dx * 2);
        return n.normalize();
    }
}

class Wheel {
    constructor(localOffsetX, localOffsetY, radius = 22) {
        this.localOffset = new Vector2D(localOffsetX, localOffsetY);
        this.pos = new Vector2D();
        this.vel = new Vector2D();
        this.radius = radius;
        this.angle = 0;
        this.angularVelocity = 0;
        
        this.onGround = false;
        this.groundNormal = new Vector2D(0, 1);
        this.contactPoint = new Vector2D();
        
        // Upgradable physics factors
        this.grip = 1.0;
    }
}

class Car {
    constructor(x, y) {
        // Chassis rigid body properties
        this.pos = new Vector2D(x, y);
        this.vel = new Vector2D(0, 0);
        this.angle = 0;
        this.angularVelocity = 0;
        
        // Physical parameters
        this.mass = 120;
        this.inertia = 12000;
        this.width = 110;
        this.height = 36;
        
        // Driver head local offset (for crash detection)
        this.driverHeadLocal = new Vector2D(0, 32); 
        this.isCrashed = false;

        // Suspension properties (Upgradable)
        this.suspensionRestLength = 45;
        this.suspensionSpringK = 1800; // Spring stiffness
        this.suspensionDampingC = 95;  // Damper constant

        // Wheels
        // Back wheel drives and brakes
        this.backWheel = new Wheel(-40, -12, 22);
        // Front wheel
        this.frontWheel = new Wheel(40, -12, 22);

        // Control inputs
        this.controls = {
            gas: 0,       // 0 to 1
            brake: 0,     // 0 to 1
            tiltLeft: false,
            tiltRight: false
        };

        // Upgradable engine/air attributes
        this.enginePower = 1800;
        this.maxSpeed = 800;
        this.airControlTorque = 4000; // Torque applied in the air for flips
        
        // Fuel settings
        this.maxFuel = 100;
        this.fuel = 100;
        this.fuelBurnRate = 4.5; // per second

        // Initialize wheel positions
        this.resetWheels();
    }

    resetWheels() {
        const rB = this.backWheel.localOffset.rotate(this.angle);
        const rF = this.frontWheel.localOffset.rotate(this.angle);
        
        this.backWheel.pos = this.pos.add(rB).add(new Vector2D(0, -this.suspensionRestLength));
        this.frontWheel.pos = this.pos.add(rF).add(new Vector2D(0, -this.suspensionRestLength));
        
        this.backWheel.vel = this.vel.clone();
        this.frontWheel.vel = this.vel.clone();
        
        this.backWheel.angularVelocity = 0;
        this.frontWheel.angularVelocity = 0;
        
        this.isCrashed = false;
        this.fuel = this.maxFuel;
    }

    update(dt, terrain) {
        if (this.isCrashed) return;

        // 1. Consume Fuel
        if (this.controls.gas > 0.05) {
            this.fuel -= this.fuelBurnRate * 1.5 * dt;
        } else {
            this.fuel -= this.fuelBurnRate * 0.6 * dt;
        }
        if (this.fuel < 0) this.fuel = 0;

        const gravityVec = new Vector2D(0, terrain.gravity);
        const wheelMass = 15;

        // Apply external forces on wheels (gravity, terrain collision)
        [this.backWheel, this.frontWheel].forEach((wheel, idx) => {
            // Apply gravity to wheel
            wheel.vel = wheel.vel.add(gravityVec.mult(dt));
            wheel.pos = wheel.pos.add(wheel.vel.mult(dt));

            // Ground collision detection
            const groundY = terrain.getHeight(wheel.pos.x);
            const normal = terrain.getNormal(wheel.pos.x);
            
            // Check if wheel intersects terrain
            // The ground normal points upwards, so if wheel center is below groundY + radius along normal, it's colliding
            const penetration = (groundY + wheel.radius) - wheel.pos.y;
            
            if (penetration > 0) {
                wheel.onGround = true;
                wheel.groundNormal = normal;
                
                // Reposition wheel to ride on top of ground
                wheel.pos.y = groundY + wheel.radius;
                
                // Normal velocity component
                const vn = wheel.vel.dot(normal);
                if (vn < 0) {
                    // Restitution (bounce resolution)
                    wheel.vel = wheel.vel.sub(normal.mult(vn * 1.05));
                }

                // Traction / Friction
                // Tangent vector pointing forward (along ground surface)
                const tangent = new Vector2D(normal.y, -normal.x);
                const vt = wheel.vel.dot(tangent);

                // Apply drive force if wheel is on ground
                let fTraction = 0;
                if (this.fuel > 0) {
                    if (idx === 0) { // Rear wheel drive
                        const targetDriveSpeed = this.controls.gas * this.maxSpeed;
                        const driveAccel = (targetDriveSpeed - vt) * 12;
                        fTraction += driveAccel * this.enginePower * 0.0008;
                    }
                    // All-wheel assist (slightly powers the front wheel too)
                    if (idx === 1 && this.controls.gas > 0) {
                        const targetDriveSpeed = this.controls.gas * this.maxSpeed * 0.8;
                        const driveAccel = (targetDriveSpeed - vt) * 8;
                        fTraction += driveAccel * this.enginePower * 0.0004;
                    }
                }

                // Apply brakes
                if (this.controls.brake > 0) {
                    fTraction -= vt * 30 * this.controls.brake;
                }

                // Friction limit based on normal force and tire grip
                const normalForce = Math.max(0, -vn * wheelMass / dt);
                const maxFriction = (normalForce + 50) * terrain.friction * wheel.grip * 1.5;
                fTraction = Math.max(-maxFriction, Math.min(maxFriction, fTraction));

                // Apply force to wheel along tangent
                wheel.vel = wheel.vel.add(tangent.mult(fTraction * dt / wheelMass));
                
                // Spin wheel based on speed along terrain
                wheel.angularVelocity = vt / wheel.radius;
            } else {
                wheel.onGround = false;
                // Wheel spin slows down in air
                wheel.angularVelocity *= 0.95;
                if (this.controls.gas > 0 && this.fuel > 0) {
                    wheel.angularVelocity += 15 * this.controls.gas * dt;
                }
            }

            // Update wheel spin angle
            wheel.angle += wheel.angularVelocity * dt;
        });

        // 2. Chassis Physics
        let totalForce = gravityVec.mult(this.mass); // Start with gravity
        let totalTorque = 0;

        // Apply suspension springs
        [this.backWheel, this.frontWheel].forEach((wheel) => {
            // World attachment point
            const r = wheel.localOffset.rotate(this.angle);
            const attachPos = this.pos.add(r);

            // Suspension vector (from attach point to wheel center)
            const suspVec = wheel.pos.sub(attachPos);
            const suspDist = suspVec.length();
            
            if (suspDist > 0) {
                const suspDir = suspVec.normalize();
                
                // Spring compression (restLength - current distance)
                const xCompression = this.suspensionRestLength - suspDist;
                
                // Relative velocity along suspension direction
                const relVel = wheel.vel.sub(this.getVelocityAtPoint(r));
                const vSpeed = relVel.dot(suspDir);

                // Damped spring force: F = k * x + c * v
                const springForceMagnitude = (this.suspensionSpringK * xCompression) + (this.suspensionDampingC * vSpeed);
                
                // Clamp spring force to avoid pulling wheel inside chassis on huge extensions
                const suspForce = suspDir.mult(Math.max(-3000, Math.min(5000, springForceMagnitude)));

                // Force on chassis is opposite of force on wheel
                // The spring pushes the wheel away from chassis, and chassis away from wheel
                totalForce = totalForce.sub(suspForce);

                // Torque = r x F
                totalTorque += r.cross(suspForce.mult(-1));

                // Push the wheel (equal and opposite to suspension force on chassis)
                wheel.vel = wheel.vel.add(suspForce.mult(dt / wheelMass));
            }
        });

        // Air controls (torque applied when vehicle is in the air)
        const inAir = !this.backWheel.onGround && !this.frontWheel.onGround;
        if (inAir) {
            // Gas spins car backward (counter-clockwise / nose up)
            if (this.controls.gas > 0 && this.fuel > 0) {
                totalTorque += this.airControlTorque * this.controls.gas;
            }
            // Brake/Reverse spins car forward (clockwise / nose down)
            if (this.controls.brake > 0) {
                totalTorque -= this.airControlTorque * this.controls.brake;
            }
        }

        // Apply keyboard tilt overrides (if any)
        if (this.controls.tiltLeft) {
            totalTorque += this.airControlTorque * 1.5;
        }
        if (this.controls.tiltRight) {
            totalTorque -= this.airControlTorque * 1.5;
        }

        // Apply rotational drag
        this.angularVelocity *= 0.98;

        // Integrate chassis movement
        this.vel = this.vel.add(totalForce.mult(dt / this.mass));
        this.pos = this.pos.add(this.vel.mult(dt));

        this.angularVelocity += (totalTorque / this.inertia) * dt;
        // Dampen angular velocity when spinning super fast to avoid physics glitches
        this.angularVelocity = Math.max(-12, Math.min(12, this.angularVelocity));
        this.angle += this.angularVelocity * dt;

        // Keep car from dropping to infinity or flying off screen left
        if (this.pos.x < 0) {
            this.pos.x = 0;
            this.vel.x = Math.max(0, this.vel.x);
        }

        // 3. Driver Head position and Crash Detection
        const driverHeadWorld = this.pos.add(this.driverHeadLocal.rotate(this.angle));
        const headGroundY = terrain.getHeight(driverHeadWorld.x);
        
        // If driver head goes below terrain, crash!
        if (driverHeadWorld.y < headGroundY + 5) {
            this.isCrashed = true;
        }
    }

    getVelocityAtPoint(r) {
        // V = V_cm + w x r
        // in 2D: w x r = (-w * r.y, w * r.x)
        return new Vector2D(
            this.vel.x - this.angularVelocity * r.y,
            this.vel.y + this.angularVelocity * r.x
        );
    }
}

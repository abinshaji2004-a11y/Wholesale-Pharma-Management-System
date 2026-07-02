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

    // Procedural terrain height at coordinate x with a flat starting runway and smooth transition
    getHeight(x) {
        const flatY = -120; // Flat platform height in physics coordinates
        const flatEnd = 250; // Runway ends here
        const blendEnd = 550; // Hills transition complete here

        if (x < flatEnd) {
            return flatY;
        } else if (x < blendEnd) {
            const t = (x - flatEnd) / (blendEnd - flatEnd);
            // Smooth-step (Hermite) interpolation for seamless transition
            const smoothT = t * t * (3 - 2 * t);
            return this.getRawHeight(x) * smoothT + (1 - smoothT) * flatY;
        } else {
            return this.getRawHeight(x);
        }
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
        this.grip = 1.15;
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
        this.inertia = 135000; // Corrected from 12000 to match the physical box inertia (1/12 * M * (W^2 + H^2))
        this.width = 110;
        this.height = 36;
        
        // Driver head local offset (for crash detection)
        this.driverHeadLocal = new Vector2D(0, 32); 
        this.isCrashed = false;

        // Suspension properties (Upgradable)
        this.suspensionRestLength = 46;
        this.suspensionSpringK = 3500; // Spring stiffness
        this.suspensionDampingC = 850;  // Damper constant (optimized for critical damping with 120kg mass)

        // Wheels
        // Back wheel drives and brakes (wheelbase widened to 92px and lower center of mass to prevent nose lifting/wheelies)
        this.backWheel = new Wheel(-46, -8, 22);
        // Front wheel
        this.frontWheel = new Wheel(46, -8, 22);

        // Control inputs
        this.controls = {
            gas: 0,       // 0 to 1
            brake: 0,     // 0 to 1
            tiltLeft: false,
            tiltRight: false
        };

        // Upgradable engine/air attributes
        this.enginePower = 2400;
        this.maxSpeed = 900;
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
        
        const suspAxis = new Vector2D(0, -1).rotate(this.angle);
        this.backWheel.pos = this.pos.add(rB).add(suspAxis.mult(this.suspensionRestLength));
        this.frontWheel.pos = this.pos.add(rF).add(suspAxis.mult(this.suspensionRestLength));
        
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

        // Initialize chassis total forces and torque (gravity starts it off)
        let totalForce = gravityVec.mult(this.mass);
        let totalTorque = 0;

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
                
                // Transfer horizontal tractive force directly to the chassis via rigid linkages
                const r = wheel.localOffset.rotate(this.angle);
                const forceChassis = tangent.mult(fTraction);
                totalForce = totalForce.add(forceChassis);
                totalTorque += r.cross(forceChassis);
                
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

        // 2. Chassis Physics - Suspension and Integration

        // Apply suspension springs projected along chassis local vertical axis
        [this.backWheel, this.frontWheel].forEach((wheel) => {
            // World attachment point
            const r = wheel.localOffset.rotate(this.angle);
            const attachPos = this.pos.add(r);

            // Suspension axis is the local down vector of the chassis: (0, -1) rotated
            const suspAxis = new Vector2D(0, -1).rotate(this.angle);

            // Vector from attachment point to wheel center
            const offset = wheel.pos.sub(attachPos);
            
            // Suspension length is the projection of the offset along the suspension axis
            let suspLength = offset.dot(suspAxis);
            
            // Hard suspension travel constraints:
            // 1. Minimum compression limit (prevent wheel-chassis overlapping)
            // 2. Maximum extension limit (prevent wheel detaching/stretching infinitely)
            const maxSuspLength = this.suspensionRestLength + 12;
            if (suspLength < 10) {
                wheel.pos = attachPos.add(suspAxis.mult(10));
                suspLength = 10;
            } else if (suspLength > maxSuspLength) {
                wheel.pos = attachPos.add(suspAxis.mult(maxSuspLength));
                suspLength = maxSuspLength;
            }

            // Spring compression (restLength - current distance along axis)
            const xCompression = this.suspensionRestLength - suspLength;

            // Relative velocity of wheel to attachment point
            const relVel = wheel.vel.sub(this.getVelocityAtPoint(r));
            
            // Speed along suspension axis
            const vSpeed = relVel.dot(suspAxis);

            // Damped spring force: F = k * x - c * v (damping must oppose the rate of compression/expansion)
            const springForceMagnitude = (this.suspensionSpringK * xCompression) - (this.suspensionDampingC * vSpeed);
            
            // Clamp spring force to keep it in a safe range (must be larger than gravity force 78,000)
            const clampedMagnitude = Math.max(-20000, Math.min(200000, springForceMagnitude));
            const suspForce = suspAxis.mult(clampedMagnitude);

            // Force on chassis is opposite to force on wheel
            // The spring pushes the chassis UP (opposite to suspAxis) and wheel DOWN (along suspAxis)
            totalForce = totalForce.sub(suspForce);

            // Torque = r x F_chassis (F_chassis = -suspForce)
            totalTorque += r.cross(suspForce.mult(-1));

            // Force on wheel is suspForce
            wheel.vel = wheel.vel.add(suspForce.mult(dt / wheelMass));
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
            // Reset wheels horizontally to prevent negative drift glitches
            this.backWheel.pos.x = Math.max(this.backWheel.pos.x, -50);
            this.backWheel.vel.x = Math.max(this.backWheel.vel.x, 0);
            this.frontWheel.pos.x = Math.max(this.frontWheel.pos.x, -50);
            this.frontWheel.vel.x = Math.max(this.frontWheel.vel.x, 0);
        }

        // 3. Driver Head position and Crash Detection
        const driverHeadWorld = this.pos.add(this.driverHeadLocal.rotate(this.angle));
        const headGroundY = terrain.getHeight(driverHeadWorld.x);
        
        // If driver head goes below terrain, check if the car is also flipped (neck flip)
        // This prevents false crashes while climbing steep hills upright
        if (driverHeadWorld.y < headGroundY + 5) {
            const angleDeg = Math.abs(this.angle * 180 / Math.PI) % 360;
            // Only crash if the chassis is tilted past 82 degrees (inverted roof area)
            if (angleDeg > 82 && angleDeg < 278) {
                this.isCrashed = true;
            }
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
